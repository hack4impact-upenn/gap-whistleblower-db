# Government Accountability Project

## Team
* Sarah Raines (Project Lead)
* Kasra Khadem (Business Development)
* Aruna Prasad
* Jediah Katz
* Amit Lohe

## Setup

##### Clone the project

```
$ git clone https://github.com/hack4impact/gap-whistleblower-db.git
$ cd gap-whistleblower-db
```
##### [Mac-only] Make sure XCode tools are installed

```
$ xcode-select --install
```

##### Add environment variables

Create a file called `.env` that contains environment variables in the following syntax: `ENVIRONMENT_VARIABLE=value`.
You may also wrap values in double quotes like `ENVIRONMENT_VARIABLE="value with spaces"`.
For example, the mailing environment variables can be set as the following.
We recommend using Sendgrid for a mailing SMTP server, but anything else will work as well.

```
MAIL_USERNAME=SendgridUsername
MAIL_PASSWORD=SendgridPassword
SECRET_KEY=SuperRandomStringToBeUsedForEncryption
```

Other key-value pairs:

* `ADMIN_EMAIL`: set to the default email for your first admin account (default is `admin@idp.com`)
* `ADMIN_PASSWORD`: set to the default password for your first admin account (default is `password`)
* `DATABASE_URL`: set to a postgresql database url (default is `data-dev.sqlite`)
* `REDISTOGO_URL`: set to Redis To Go URL or any redis server url (default is `http://localhost:6379`)
* `RAYGUN_APIKEY`: api key for raygun (default is `None`)
* `FLASK_CONFIG`: can be `development`, `production`, `default`, `heroku`, `unix`, or `testing`. Most of the time you will use `development` or `production`.


**Note: do not include the `.env` file in any commits. This should remain private.**

##### Install the dependencies

```
brew install pipenv
pipenv --python 3.7
pipenv install
```

##### Other dependencies for running locally

You need [Redis](http://redis.io/), and [Sass](http://sass-lang.com/). Chances are, these commands will work:


**Sass:**

```
$ gem install sass
```

**Redis:**

_Mac (using [homebrew](http://brew.sh/)):_

```
$ brew install redis
```

_Linux:_

```
$ sudo apt-get install redis-server
```

You will also need to install **PostgresQL**

_Mac (using homebrew):_

```
brew install postgresql
```

_Linux (based on this [issue](https://github.com/hack4impact/flask-base/issues/96)):_

```
sudo apt-get install libpq-dev
```


##### Create the database

```
$ python manage.py recreate_db
```

##### Other setup (e.g. creating roles in database)

```
$ python manage.py setup_dev
```

Note that this will create an admin user with email and password specified by the `ADMIN_EMAIL` and `ADMIN_PASSWORD` config variables. If not specified, they are both `admin@idp.com` and `password` respectively.

##### [Optional] Add fake data to the database

```
$ python manage.py add_fake_data
```

## Running the app

```
$ source env/bin/activate
$ honcho start -f Local
```

For Windows users having issues with binding to a redis port locally, refer to [this issue](https://github.com/hack4impact/flask-base/issues/132).

## Formatting code

Before you submit changes, autoformat your code with `python manage.py format`.

## License
[MIT License](LICENSE.md)

