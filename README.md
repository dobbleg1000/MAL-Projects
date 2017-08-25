# MAL-Projects
Just some basic python applications I wrote for fun.

Background.py - Generates a Wallpaper from the airing shows on your currently watching shows. Currently no algorithm for number of divisions. --username to give username or answer the prompt. If the prompt is blank it defaults to config username

Broken.json - Mal.py uses the tvdb to get show airing info. Some of these shows are broken and this file contains the correct info

idMemoizer.py - Mal's api can be kind of slow some times. This file will take your account and cache the object from all of your shows.

image_stuff.py - Helper file for Background.py

Mal.py - Needs to be renamed. What it currently does is gives you a countdown till all the shows on your currently watching and are airing air for that week.

covers\ - location of the pictures needed by Background.py and where it will save the title art for shows.

bins\ - location for the caches and a template label for the days of the week.

# Config
In order for you to use any of these files you must create a config.json with this info inside

{
    "UserName": "YOUR_USERNAME",
    "Password": "YOUR_Password"
}
