def main():
    try:
        from simple_repository_server.cli import main as server_main
    except ImportError:
        print("Install simple-repository-server to run a development repository server")
        exit(1)
    server_main()


if __name__ == '__main__':
    main()
