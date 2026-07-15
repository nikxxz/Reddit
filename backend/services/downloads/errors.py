class DownloadError(RuntimeError):
    pass


class UrlSafetyError(DownloadError):
    pass


class DownloadCancelled(DownloadError):
    pass
