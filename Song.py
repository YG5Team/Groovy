class Song:
    def __init__(self, title, url, id):
        self.title = title
        self.url = url
        self.id = id

    def __str__(self):
        return f'{self.title} {self.url} {self.id}'