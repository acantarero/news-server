# News Server Documentation

*Last Updated: 2014-12-17 by Alejandro Cantarero*.

This document describes how to configure and start the news server processes as well as how to access them.

## Requirements

+ Python 3.4
+ Oracle Java 7
+ Cassandra 2.0+
+ CQL 3.0+
+ MongoDB 2.6.3+

## Running the Webserver


#### Restarting the Webserver

After updating files on the server, the server can be restarted with

`service apache2 reload`

#### Logs

Apache logs can be found at `/var/log/apache2/error.log` and `/var/www/log`.  Webserver logs can be found at:

+ **./log/error.log**   logs error that forced services to restart
+ ** ./log/api.log **  log files for api and database services
+ ** ./log/noozli.log ** log files for the scraper

## The Web Scraper

### Running

Run the webscraper in the background on the server.

```
$> nohup python rss.py &
```

Status is written to `./log/noozli.log`.

### Developing

When developing on the webscraper, run it local in debug mode.  This will prevent it from adding data to the database and will return all the results for review.

```
In [1]:  results = rss.run(debug=True)
```

The webscraper has a mongo database called `noozli_test` and a collection called `webscraper`.  These are currently only stored locally, not available on the server.   The `webscraper` collection has a set of example web sites from all different sources that exercise different parts of the scraper.   When adding a new website, it is important to find all the different versions of pages that exercise your new code and the old aspects of the code as well and add them to this test collection.

```
In [2]: rss.add_test_case(results[4])
```

You can run the full set of tests from the command line in the `/tests` folder as follows

```
$> nosetests test_scraper.py
```

After adding a new website to the scraper, be sure to re-run the test suite to make sure no previous sites were broken.

## API Documentation

Current version is 1.0.  All endpoints are available at `localhost:8080/1.0` unless otherwise noted.  All requests return json formatted data.  Required parameters and returned fields are described below.

Available end points:

### Articles

Resource | Description
---------|------------
GET articles | Returns new articles for the user

**GET articles**

Returns new articles that have not been previously sent to the user.  May return fewer articles than requested.  Check the returned count for the number of matched articles that were returned.   

Note: This currently available at a different URL as we migrate from the existing version to the current version.

Required parameters:

+ `user_id`  unique user id
+ `count`  requested number of articles

Returns:

+ `count`  number of articles returned
+ `articles` list of articles in JSON format

Articles returned from this end point have the following fields:

+ `article_id`  unique identifying string per article
+ `display_text`  html formatted text
+ `image`  link to the article image
+ `link`  link to the article
+ `published`  time article was published
+ `source`  name of the RSS feed article came from
+ `title`  title of article


`http://localhost:8080/1.0/articles?count=2&user_id=0368fd29-553e-47e1-bd8f-5857f848b859`

Example output

```
{
  articles: [
    {
      article_id: "df243a0b7de682044555fae4229d36f3",
      display_text: "<div class="cnn_storyarea" id="cnnContentContainer"> <div class="cnn_stryarblkbr"></div> <div class="cnn_strybtntools"> <div id="cnn_sharebar1"> </div> </div> <!--google_ad_section_start--><!--startclickprintinclude--> <!--endclickprintinclude--><!--startclickprintexclude--> <div class="cnn_stryathrtmp"><div class="cnn_story_attribution"><table border="0" cellpadding="0" cellspacing="0"><tbody><tr valign="bottom"> <td style="vertical-align:bottom;"> <div class="cnn_strycblnk"></div> <!-- no specific author value --> </td> <td style="vertical-align:bottom;"> <div class="cnn_story_author"> </div> <div class="cnn_clear"></div> </td> </tr></tbody></table></div></div> <!--google_ad_section_end--> <div class="cnn_strycntntlft"> <!--startclickprintexclude--> <div class="cnnExplainer cnn_html_slideshow"> <div class="cnnstrylccimg640"><div class="cnn_stryichgfull"><div class="cnn_stryichgflg"> <div class="cnn_clear"></div> </div></div></div> <div class="cnn_gallery_divline"></div> <div style="background-color:#000;color:#FFF;height:27px"> <div class="cnn_clear"></div> </div> </div> <a name="em0"></a> <!--endclickprintexclude--><!--google_ad_section_start--><!--startclickprintinclude--> <p><strong>(CNN)</strong> -- For 17 years, NASA rovers have laid down tire tracks on Mars. But details the space agency divulged this week about its next Martian exploration vehicle underscored NASA's ultimate goal.</p> <p class="cnn_storypgraphtxt cnn_storypgraph2">Footprints are to follow someday.</p> <p class="cnn_storypgraphtxt cnn_storypgraph3">The last three rovers -- Spirit, Opportunity and Curiosity -- confirmed the Red Planet's ability to support life and searched for signs of past life.</p> <p class="cnn_storypgraphtxt cnn_storypgraph4">The Mars rover of the next decade will hone in on ways to sustain future life there, human life.</p> <p class="cnn_storypgraphtxt cnn_storypgraph5">"The 2020 rover will help answer questions about the Martian environment that astronauts will face and test technologies they need before landing on, exploring and returning from the Red Planet," said NASA's William Gerstenmaier who works on human missions.</p> <p class="cnn_storypgraphtxt cnn_storypgraph6">This will include experiments that convert carbon dioxide in the Martian atmosphere into oxygen "for human respiration."</p> <p class="cnn_storypgraphtxt cnn_storypgraph7">Oxygen could also be used on Mars in making rocket fuel that would allow astronauts to refill their tanks.</p> <p class="cnn_storypgraphtxt cnn_storypgraph8"><strong>Twin rovers</strong></p> <p class="cnn_storypgraphtxt cnn_storypgraph9">The 2020 rover is the near spitting image of Curiosity and NASA's Jet Propulsion Laboratory announced plans to launch the new edition not long after Curiosity landed on Mars in 2012.</p> <p class="cnn_storypgraphtxt cnn_storypgraph10">But the 2020 rover has new and improved features. The Mars Oxygen ISRU Experiment, or MOXIE for short, is just one.</p> <a name="em2"></a> <a name="em3"></a> <p class="cnn_storypgraphtxt cnn_storypgraph11">There are super cameras that will send back 3D panoramic images and spectrometers that will analyze the chemical makeup of minerals with an apparent eye to farming.</p> <a name="em4"></a> </div></div>",
      full_text: "(CNN) -- For 17 years, NASA rovers have laid down tire tracks on Mars. But details the space agency divulged this week about its next Martian exploration vehicle underscored NASA's ultimate goal. Footprints are to follow someday. The last three rovers -- Spirit, Opportunity and Curiosity -- confirmed the Red Planet's ability to support life and searched for signs of past life. The Mars rover of the next decade will hone in on ways to sustain future life there, human life. "The 2020 rover will help answer questions about the Martian environment that astronauts will face and test technologies they need before landing on, exploring and returning from the Red Planet," said NASA's William Gerstenmaier who works on human missions. This will include experiments that convert carbon dioxide in the Martian atmosphere into oxygen "for human respiration." Oxygen could also be used on Mars in making rocket fuel that would allow astronauts to refill their tanks. Twin rovers The 2020 rover is the near spitting image of Curiosity and NASA's Jet Propulsion Laboratory announced plans to launch the new edition not long after Curiosity landed on Mars in 2012. But the 2020 rover has new and improved features. The Mars Oxygen ISRU Experiment, or MOXIE for short, is just one. There are super cameras that will send back 3D panoramic images and spectrometers that will analyze the chemical makeup of minerals with an apparent eye to farming.",
      image: "http://i2.cdn.turner.com/cnn/dam/assets/140801073430-nasa-mars-2020-rover-story-top.jpg",
      link: "http://www.cnn.com/2014/08/01/tech/innovation/mars-2020-rover/",
      published: "Sat, 02 Aug 2014 01:07:48 EDT",
      source: "CNN.com - U.S.",
      title: "NASA's next rover to Mars will make oxygen and look for farmland"
    }
  ],
  count: 1
}
```
### Users

Resource | Description
---------|-----------
GET users | Creates new user in the database and returns their id
POST users | Send engagement analytics on each article to the server


#### GET users

Request:

`curl -X GET http://localhost:8080/1.0/users`

Returns:

```
{
  value: "0368fd29-553e-47e1-bd8f-5857f848b859"
}
```

#### POST users

Send engagement analytics for each article from the app.  Analytics can be sent for single or multiple articles per call.  

Example of sending analytics for a single article.

```
curl -X POST http://127.0.0.1:8080/1.0/users -H "Content-Type:application/json" -d '{"count": 1, "user_id": "e438e598-ba5a-4528-935a-7f9c17e66a0", "articles": [{"article_id": "fcce9e950368569c72d1dae0c3023a94", "action": "done", "total_time": 30, "time_zero": 3}]}'
```

Note that the `content-type` in the POST header must be set to `application/json`.  Data posted is a json document with the following format:

```
{
    "count": <int>,
    "user_id": <string>,
    "articles":
        [
            {<article analytics 1>},
            ...
            {<article analytics n>}
        ]
}
```

Required fields in the JSON:

+ `count`  **int**  number of articles for which analytics data is being transmitted.  *Must* match the length of the `articles` list
+ `user_id` **string**  unique id for the user who interacted with the articles
+ `articles` **list<json/dict>** list of additional objects / dictionaries, each one corresponding to a single article

Article analytics JSONs have the following required and optional fields.  Note that if optional fields are not included they are set to zero if the type is an `int` or to an empty list if the type is a `list`

Required fields

+ `article_id` **string** unique id for the article
+ `action`  **string**  action taken for article, one of 'save' or 'done'
+ `total_time` **integer**  total time in seconds spent on article
+ `time_zero` **integer**  time in seconds before any action was taken

Optional fields

+ `percent` **integer**  percent of article that was scrolled through as an integer (0 to 100)
+ `up` **integer**  number of up swipes
+ `down` **integer**  number of down swipes
+ `shared` **list<string>** list of sharing actions taken.  Send empty list `[]` if none were taken.  Sharing options may be one of:  'facebook', 'twitter', or 'email', e.g. `"shared": ["twitter", "email"]`

Returns success if POST request was accepted.

`{'status':  200, 'message': 'success'}`

Example of calling the end point from python for a single article

POST requests that fail due to missing or incorrectly formatted data return code 404 along with an error message.

Example of sending analytics for multiple articles to the server:

```
curl -X POST http://127.0.0.1:8080/1.0/users -H "Content-Type:application/json" -d '{"count": 3, "user_id": "e438e598-ba5a-4528-935a-7f9c17ee66a0", "articles": [{"article_id": "fcce9e950368569c72d1dae0c3023a94", "action": "done", "total_time": 30, "time_zero": 3, "percent": 35, "down": 5, "up": 1, "share": ["twitter"]}, {"article_id": "82347ece1f9f4996291ba38982ee435b", "action": "save", "total_time": 15, "time_zero": 13, "percent": 75, "down": 1, "up": 0, "share": ["facebook", "twitter"]}, {"article_id": "7522eeb2cf78202b01425783438cd3be", "action": "done", "total_time": 140, "time_zero": 33, "percent": 5, "down": 3, "up": 2, "share": []}]}'
```
