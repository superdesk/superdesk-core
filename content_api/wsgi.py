from content_api.app import get_app

application = get_app()

app = get_app()
app.run(host='0.0.0.0', port=5400, debug=True, use_reloader=True)
