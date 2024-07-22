# CONTRIBUTING

## Instructions for contributors

1. Clone the [GitHub](https://github.com/rAPIdy-org/rAPIdy) repository 
2. Setup your machine with the required development environment
   - `virtualenv -p python3 .venv`
   - `source .venv/bin/activate`
   - `python3 -m pip install -r requirements.txt`
   - `python3 -m poetry install`
   - `pre-commit install`
3. Make a change
4. Make sure all tests passed
   - `python3 -m pytest`
5. Add a file into the CHANGES folder, named after the ticket or PR number
