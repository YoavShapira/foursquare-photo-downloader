from flask import Flask, redirect, request
import foursquare

app = Flask(__name__)

@app.route("/")
def hello():
        # Construct the client object
    client = foursquare.Foursquare(client_id='TXYHWCBRAUJD4PURIN01RLKXIE5N1SO5WKMNMIDOAUQTEBZR',
        client_secret='E4N3Q5HH4GFN0JSTY1UN2UDF0GGIKG5JCEIS005RNNMHWSM3',
        redirect_uri='http://localhost:5000/auth')

    # Build the authorization url for your app
    auth_uri = client.oauth.auth_url()

    return redirect(auth_uri)

@app.route("/auth")
def auth():
    code = request.args.get('code', 'N/A')
    return "Authorized, code = %s" % code

if __name__ == "__main__":
    app.debug = True
    app.run()
