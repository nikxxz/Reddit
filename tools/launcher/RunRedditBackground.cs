using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

internal static class RunRedditBackground
{
    [STAThread]
    private static int Main()
    {
        string root = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);

        if (!File.Exists(Path.Combine(root, "frontend-react", "dist", "index.html")))
        {
            MessageBox.Show(
                "frontend-react\\dist\\index.html was not found.\n\nRun this once first:\ncd frontend-react\nnpm.cmd run build",
                "Reddit Media Downloader",
                MessageBoxButtons.OK,
                MessageBoxIcon.Warning);
            return 1;
        }

        string pythonExe = FindPython(root);
        if (pythonExe == null)
        {
            MessageBox.Show(
                "Python was not found.\n\nInstall Python, or create .venv and install requirements:\npython -m venv .venv\n.venv\\Scripts\\python.exe -m pip install -r requirements.txt",
                "Reddit Media Downloader",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            return 1;
        }

        var startInfo = new ProcessStartInfo
        {
            FileName = pythonExe,
            Arguments = "run.py",
            WorkingDirectory = root,
            UseShellExecute = false,
            CreateNoWindow = true,
            WindowStyle = ProcessWindowStyle.Hidden
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

        try
        {
            Process process = Process.Start(startInfo);
            if (process != null)
            {
                try
                {
                    process.PriorityClass = ProcessPriorityClass.BelowNormal;
                }
                catch
                {
                    // Priority changes can be denied by Windows policy; startup still succeeded.
                }
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                "Unable to start Reddit Media Downloader.\n\n" + ex.Message,
                "Reddit Media Downloader",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            return 1;
        }

        return 0;
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
