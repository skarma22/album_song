from django.db import models


class SongData(models.Model):
    main_title = models.CharField(max_length=255)
    lyrics_content = models.TextField()
    expert = models.CharField(max_length=255)
    featuring_detail = models.CharField(max_length=255)
    album = models.CharField(max_length=255)
    release_date = models.CharField(max_length=255)
    genius_link = models.URLField()