# FIWARE Trial Users Management Tests

Folder for acceptance tests of the FIWARE Trial Users Management.

## How to Run the Acceptance Tests

### Prerequisites:

- Python 2.7 or newer

- pip installed (http://docs.python-guide.org/en/latest/starting/install/linux/)

- virtualenv installed (pip install virtalenv)

- Git installed (yum install git-core / apt-get install git)

### Environment preparation:

- Create a virtual environment somewhere, e.g. in ENV (virtualenv ENV)

- Activate the virtual environment (source ENV/bin/activate)

- Change to the test/acceptance folder of the project

- Install the requirements for the acceptance tests in the virtual environment (pip install -r requirements.txt --allow-all-external).

- Configure file in tests/acceptance_tests/commons/configuration.py adding the keystone url, and a valid, user, password and tenant ID.

### Tests execution:

- Change to the tests/acceptance_tests folder of the project if not already on it

- Run lettuce_tools with appropriate params (see available ones with the -h option)

