from manager.api.app import create_app

def main():
    app = create_app()
    app.run(host='127.0.0.1', port=8080)


if __name__ == "__main__":
    main()
