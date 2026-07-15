from types import SimpleNamespace


def submission(**overrides):
    values = {
        "id": "abc123",
        "title": "A test post",
        "subreddit": SimpleNamespace(display_name="pics"),
        "author": "tester",
        "created_utc": 1712345678,
        "permalink": "/r/pics/comments/abc123/a_test_post/",
        "url": "https://example.com/post",
        "over_18": False,
        "is_video": False,
        "is_gallery": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def direct_image_submission():
    return submission(url="https://i.redd.it/example.jpg", thumbnail="self")


def reddit_video_submission():
    return submission(
        is_video=True,
        media={
            "reddit_video": {
                "fallback_url": "https://v.redd.it/video/DASH_720.mp4",
                "width": 1280,
                "height": 720,
                "duration": 28,
            }
        },
    )


def gif_submission():
    return submission(url="https://i.redd.it/loop.gif")


def gallery_submission():
    return submission(
        is_gallery=True,
        gallery_data={"items": [{"media_id": "image1"}, {"media_id": "image2"}]},
        media_metadata={
            "image1": {
                "s": {
                    "u": "https://i.redd.it/gallery1.jpg",
                    "x": 1920,
                    "y": 1080,
                },
                "p": [{"u": "https://preview.redd.it/gallery1-preview.jpg"}],
            }
        },
    )


def text_submission():
    return submission(url="https://www.reddit.com/r/pics/comments/abc123/")


def deleted_author_submission():
    return submission(author=None, url="https://i.redd.it/example.png")


def escaped_preview_submission():
    return submission(
        url="https://i.redd.it/example.webp",
        preview={
            "images": [
                {
                    "source": {
                        "url": "https://preview.redd.it/image.jpg?width=640&amp;crop=smart"
                    }
                }
            ]
        },
    )


def unsupported_submission():
    return submission(url="https://example.com/page.html")


def crosspost_submission():
    return submission(
        id="crosspost",
        title="Crossposted title",
        url="https://www.reddit.com/r/pics/comments/crosspost/",
        crosspost_parent_list=[
            {
                "id": "parent",
                "title": "Parent title",
                "subreddit": "itookapicture",
                "author": "parent_author",
                "created_utc": 1712345600,
                "permalink": "/r/itookapicture/comments/parent/title/",
                "url": "https://i.redd.it/parent.jpg",
                "over_18": False,
                "is_video": False,
                "is_gallery": False,
            }
        ],
    )
