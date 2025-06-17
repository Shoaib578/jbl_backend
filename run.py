from app import create_app

# Creates instance of Flask app using factory function
app = create_app()

if __name__ == '__main__':
    # Runs Flask development server in debug mode
    # Debug move provides an interactive debugger and automatic reloads on code changes
    # Binded to 0.0.0.0 to make app accessible from outside the container
    # app.run(debug=True, host="0.0.0.0")
    app.run(debug=True,port=80)