# 抓取新闻定时任务
from django.core.management.base import BaseCommand
import time
from news.tasks import fetch_news_and_clean


class Command(BaseCommand):
    help = "Fetch RSS news and clean old data. Use --loop to run periodically."

    def add_arguments(self, parser):
        parser.add_argument('--loop', action='store_true', help='Run continuously')
        parser.add_argument('--interval', type=int, default=3600, help='Seconds between runs when --loop')

    def handle(self, *args, **options):
        if options['loop']:
            self.stdout.write(f"Start loop, interval={options['interval']}s")
            while True:
                try:
                    fetch_news_and_clean()
                    self.stdout.write(f"Fetched and cleaned at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                except Exception as e:
                    self.stderr.write(f"Error: {e}")
                time.sleep(options['interval'])
        else:
            fetch_news_and_clean()
            self.stdout.write("Fetch and clean complete")

