# Copyright (C) 2023, CERN
# This software is distributed under the terms of the MIT
# licence, copied verbatim in the file "LICENSE".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

def main():
    try:
        from simple_repository_server.cli import main as server_main
    except ImportError:
        print("Install simple-repository-server to run a development repository server")
        exit(1)
    server_main()


if __name__ == '__main__':
    main()
