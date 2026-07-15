class DownloadError(RuntimeError):
    pass


class UrlSafetyError(DownloadError):
    pass
