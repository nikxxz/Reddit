using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Windows.Forms;

internal static class RunRedditBackground
{
    private const string AppTitle = "Reddit Media Downloader";
    private const string AppUrl = "http://127.0.0.1:8000";

    [STAThread]
    private static int Main()
    {
        string root = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);

        if (!File.Exists(Path.Combine(root, "frontend-react", "dist", "index.html")))
        {
            MessageBox.Show(
                "frontend-react\\dist\\index.html was not found.\n\nRun this once first:\ncd frontend-react\nnpm.cmd run build",
                AppTitle,
                MessageBoxButtons.OK,
                MessageBoxIcon.Warning);
            return 1;
        }

        string pythonExe = FindPython(root);
        if (pythonExe == null)
        {
            MessageBox.Show(
                "Python was not found.\n\nInstall Python, or create .venv and install requirements:\npython -m venv .venv\n.venv\\Scripts\\python.exe -m pip install -r requirements.txt",
                AppTitle,
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            return 1;
        }

        Process backendProcess;
        try
        {
            backendProcess = StartBackend(root, pythonExe);
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                "Unable to start Reddit Media Downloader.\n\n" + ex.Message,
                AppTitle,
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            return 1;
        }

        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new TrayApplicationContext(backendProcess));
        return 0;
    }

    private static Process StartBackend(string root, string pythonExe)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = pythonExe,
            Arguments = "run.py",
            WorkingDirectory = root,
            UseShellExecute = false,
            CreateNoWindow = true,
            WindowStyle = ProcessWindowStyle.Hidden,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };

        startInfo.EnvironmentVariables["DEBUG"] = "false";
        startInfo.EnvironmentVariables["APP_HOST"] = "127.0.0.1";
        startInfo.EnvironmentVariables["APP_PORT"] = "8000";
        startInfo.EnvironmentVariables["LIBRARY_RECONCILE_ON_STARTUP"] = "false";
        startInfo.EnvironmentVariables["GENERATE_MISSING_THUMBNAILS_ON_STARTUP"] = "false";
        startInfo.EnvironmentVariables["LIBRARY_RECONCILE_MAX_CONCURRENCY"] = "1";
        startInfo.EnvironmentVariables["THUMBNAIL_REGEN_MAX_CONCURRENCY"] = "1";
        startInfo.EnvironmentVariables["MAX_CONCURRENT_DOWNLOADS"] = "1";
        startInfo.EnvironmentVariables["MAINTENANCE_INTERVAL_MINUTES"] = "60";

        Process process = Process.Start(startInfo);
        if (process == null)
        {
            throw new InvalidOperationException("Windows did not return a backend process.");
        }

        process.OutputDataReceived += delegate(object sender, DataReceivedEventArgs args)
        {
            AppendLog(root, "RunRedditBackground.log", args.Data);
        };
        process.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs args)
        {
            AppendLog(root, "RunRedditBackground.err.log", args.Data);
        };
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();

        try
        {
            process.PriorityClass = ProcessPriorityClass.BelowNormal;
        }
        catch
        {
            // Priority changes can be denied by Windows policy; startup still succeeded.
        }

        return process;
    }

    private static void AppendLog(string root, string fileName, string line)
    {
        if (line == null)
        {
            return;
        }

        try
        {
            File.AppendAllText(Path.Combine(root, fileName), line + Environment.NewLine);
        }
        catch
        {
            // Logging should never keep the launcher from running.
        }
    }

    private sealed class TrayApplicationContext : ApplicationContext
    {
        private readonly Process backendProcess;
        private readonly NotifyIcon notifyIcon;
        private readonly Timer backendMonitor;
        private bool exiting;

        public TrayApplicationContext(Process backendProcess)
        {
            this.backendProcess = backendProcess;

            var menu = new ContextMenuStrip();
            menu.Items.Add("Open", null, HandleOpen);
            menu.Items.Add("Exit", null, HandleExit);

            notifyIcon = new NotifyIcon
            {
                ContextMenuStrip = menu,
                Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath) ?? SystemIcons.Application,
                Text = AppTitle,
                Visible = true
            };
            notifyIcon.DoubleClick += HandleOpen;
            notifyIcon.ShowBalloonTip(2500, AppTitle, "Running in the background. Right-click for options.", ToolTipIcon.Info);

            backendMonitor = new Timer { Interval = 2000 };
            backendMonitor.Tick += HandleBackendMonitorTick;
            backendMonitor.Start();
        }

        private void HandleOpen(object sender, EventArgs eventArgs)
        {
            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = AppUrl,
                    UseShellExecute = true
                });
            }
            catch (Exception ex)
            {
                MessageBox.Show("Unable to open the app.\n\n" + ex.Message, AppTitle, MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void HandleExit(object sender, EventArgs eventArgs)
        {
            exiting = true;
            backendMonitor.Stop();
            notifyIcon.Visible = false;
            notifyIcon.Dispose();
            StopBackend();
            ExitThread();
        }

        private void HandleBackendMonitorTick(object sender, EventArgs eventArgs)
        {
            if (exiting || !backendProcess.HasExited)
            {
                return;
            }

            exiting = true;
            backendMonitor.Stop();
            notifyIcon.ShowBalloonTip(4000, AppTitle, "The background server stopped.", ToolTipIcon.Warning);
            notifyIcon.Visible = false;
            notifyIcon.Dispose();
            ExitThread();
        }

        private void StopBackend()
        {
            try
            {
                if (backendProcess.HasExited)
                {
                    return;
                }

                backendProcess.CloseMainWindow();
                if (!backendProcess.WaitForExit(5000))
                {
                    backendProcess.Kill();
                    backendProcess.WaitForExit(5000);
                }
            }
            catch
            {
                // Exit should not fail because shutdown cleanup hit a Windows process race.
            }
            finally
            {
                backendProcess.Dispose();
            }
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                backendMonitor.Dispose();
                notifyIcon.Dispose();
                backendProcess.Dispose();
            }

            base.Dispose(disposing);
        }
    }

    private static string FindPython(string root)
    {
        string[] candidates =
        {
            Path.Combine(root, ".venv", "Scripts", "python.exe"),
            Path.Combine(root, ".venv", "Scripts", "pythonw.exe"),
            FindOnPath("python.exe"),
            FindOnPath("pythonw.exe")
        };

        foreach (string candidate in candidates)
        {
            if (!string.IsNullOrWhiteSpace(candidate) && File.Exists(candidate))
            {
                return candidate;
            }
        }

        return null;
    }

    private static string FindOnPath(string fileName)
    {
        string pathValue = Environment.GetEnvironmentVariable("PATH") ?? "";
        foreach (string directory in pathValue.Split(Path.PathSeparator))
        {
            if (string.IsNullOrWhiteSpace(directory))
            {
                continue;
            }

            try
            {
                string candidate = Path.Combine(directory.Trim(), fileName);
                if (File.Exists(candidate))
                {
                    return candidate;
                }
            }
            catch
            {
                // Ignore malformed PATH entries.
            }
        }

        return null;
    }
}
