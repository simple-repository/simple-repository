if __name__ == '__main__':
    try:
        from simple_repository_server.cli import main
    except ImportError:
        print("Install simple-repository-server to run a development repository instance.")
        exit(1)
    main()
