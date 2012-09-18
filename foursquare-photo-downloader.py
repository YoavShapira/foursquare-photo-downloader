from flask import Flask, redirect, request
import foursquare
import httplib2
import logging
import os
import simplejson as json
import urlparse

# Globals

# The Flask app object for local development
app = Flask(__name__)

# Destination directory for saved images.
# Default = /tmp, but should make configurable
dest_dir = '/tmp/'

# Limit (upper bound) on total photos to process
max_photos = 1000

# How many photos per batch. Foursquare API limit is 200.
photos_per_call = 100


@app.route("/")
def hello():
    """ Called by Flask on requests to /, the home page. Redirects to auth on Foursquare."""
    # Construct the client object
    client = foursquare.Foursquare(client_id='TXYHWCBRAUJD4PURIN01RLKXIE5N1SO5WKMNMIDOAUQTEBZR',
        client_secret='E4N3Q5HH4GFN0JSTY1UN2UDF0GGIKG5JCEIS005RNNMHWSM3',
        redirect_uri='http://localhost:5000/auth')

    # Build the authorization url for your app
    auth_uri = client.oauth.auth_url()

    return redirect(auth_uri)

@app.route("/auth")
def auth():
    """ Does most of the work. Called after auth, starts the photo downloading process. """
    code = request.args.get('code', 'N/A')
    if not code:
        app.logger.error("Could not get OAuth request token from request.")
        return "Sorry, an error occurred."
    app.logger.debug("Authorized from Foursquare, auth code = %s" % code)

    # Construct the client object
    client = foursquare.Foursquare(client_id='TXYHWCBRAUJD4PURIN01RLKXIE5N1SO5WKMNMIDOAUQTEBZR',
        client_secret='E4N3Q5HH4GFN0JSTY1UN2UDF0GGIKG5JCEIS005RNNMHWSM3',
        redirect_uri='http://localhost:5000/auth')

    # Interrogate foursquare's servers to get the user's access_token
    access_token = client.oauth.get_token(code)
    if not access_token:
        app.logger.error("Sorry, could not get OAuth access_token from request.")
    app.logger.debug("Got Foursquare OAuth access token = %s", access_token)

    # Apply the returned access token to the client
    client.set_access_token(access_token)

    # Get the user's data
    user = client.users()
    if not user:
        app.logger.error("Could not get user information after authenticating.")
        return "Sorry, an error occured."
    app.logger.debug("Got authenticated user from Foursquare = %s", json.dumps(user, sort_keys=True, indent=4 * ' '))
    app.logger.debug("User first name = %s", user['user']['firstName'])

    result = get_photos(client)
    return "Processed %d photos for %s %s" % (result, user['user']['firstName'], user['user']['lastName'])

def get_photos(client):
    # Get the user's photos, one batch at a time, until done
    offset = 0
    total_photos_processed = 0
    while (offset < max_photos):
        app.logger.info("Getting next batch of %d (max) photos at offset = %d" % (photos_per_call, offset))
        photos = client.users.photos(params={'limit': photos_per_call, 'offset': offset})
        batch_photos_processed = process_photos(photos)
        if (batch_photos_processed < 1):
            app.logger.error("Error processing photos.")
            return total_photos_processed

        # Otherwise, increment offset for next call
        offset += batch_photos_processed + 1

    return total_photos_processed

def process_photos(photos):
    """ Processes the given photos. Finds and downloads the Foursquare photos. Returns something to display to user. """

    if not photos:
        app.logger.error("Could not get user's photos from Foursquare.")
        return 0
    app.logger.debug("Photos JSON = %s" % json.dumps(photos, sort_keys=True, indent=4 * ' '))

    photos_dict = photos['photos']
    app.logger.debug('photos_dict = %s', json.dumps(photos_dict, sort_keys=True, indent = 4 * ' '))

    photo_count = photos_dict['count']
    if not photo_count:
        app.logger.error("No photo count from Foursquare?")
        return 0
    if photo_count < 1:
        app.logger.warning("No photos found for this user.")
        return 0
    app.logger.debug("Need to process %d photos total, %d this batch." % (photo_count, photos_per_call))
 
    photos_collection = photos_dict['items']
    photos_processed = 0
    for photo in photos_collection:
        process_photo(photo)
        photos_processed += 1
        app.logger.info("Done %d out of %d photos." % (photos_processed, photos_per_call))
 
    return photos_processed

def process_photo(photo):
    """ Processes the given photo. """
    if not photo:
        app.logger.error("No photo provided.")
        return False

    # Sanity-check fields we require in each photo: venue name, URL, ID
    if not photo['id']:
        app.logger.error("Photo without ID?")
        return False

    if not photo['url']:
        app.logger.error("Photo without URL?")
        return False
    else:
        url = photo['url']
        
    if not photo['venue']:
        venue = 'NoVenue'
    else:
        venue = photo['venue']['name']
    
    app.logger.info("Downloading photo from url = %s, venue name = %s" % (url, venue))

    # Extract photo file extension from URL (not ideal, content-type is better...)
    path = urlparse.urlparse(url).path
    ext = os.path.splitext(path)[1]
    if not ext:
        app.logger.warning("No file extension from path = %s", path)
        return False

    # Replace spaces in venue names with underscores for better file names
    venue = venue.replace(' ', '_')
 
    # Download photo and save it locally
    # TODO: parallelize downloads for performance?
    try:
        h = httplib2.Http(".cache")
        resp, content = h.request(url, 'GET')

        f = open('/tmp/' + venue + '_' + photo['id'] + ext, 'w')
        f.write(content)
        f.close()
    except:
        app.logger.error("Could not download photo or save it, url = %s", url)
        return False

    # If we got here, we're done with this photo.
    app.logger.debug("Done processing photo from url = %s", url)
    return True

if __name__ == "__main__":
    app.debug = True
    app.logger.setLevel(logging.INFO)
    app.run()
