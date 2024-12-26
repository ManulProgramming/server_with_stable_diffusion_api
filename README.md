# Information
![webserver_home_page](https://github.com/user-attachments/assets/abcb650c-5c98-462a-94b0-f34aab42cace)

This is a website created for entertainment purposes, which acts as a server for [AUTOMATIC1111 Stable Diffusion web UI API](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/API). Upon entering the website, users from different devices and regions are authorized a randomly assigned color to them by the server. Users can send their prompts and the resolutions for images they want to generate. There is also an admin, that is registered to a specific device before the website is even hosted. When users send prompts, the admin will receive them and be responsible for allowing or denying prompts for sending them forward to the Stable Diffusion web UI API. Users will not see their generated images, as the main idea behind it was to keep them a secret until the admin will show all of them from /receive_prompts/generated_images folder in the presentation form.

This project is nothing too serious, however, it does contain some implementations, that might be useful in other projects and creations. Such implementations are:

- Non-traditional authorization method using user-agents, IP addresses and headers from the user's browser.
- Usage of local SQLite database in Flask to store user profiles and prompts created by them.
- Encryption of sensitive data using argon2, such as users' IP addresses.
- Dividing the website part and Stable Diffusion web UI API into two different programs and connecting them using the socket library.
- Additional use of Flask-Session to separate different user's clients and frontends.

These parts and scripts can be somewhat useful in some scenarios and circumstances. I will go into details about each of them:

### Non-traditional authorization method

As I described previously, upon loading into the homepage, users will receive the corresponding color for their profile. Each user will have their own individual colour, there will be no duplicates. This trick is done using user agents, IP addresses and headers from the user's browser, which can be called the user's "fingerprints". Flask allows to receive this information using flask.request every time the user loads into the page. When the user enters the website, the script automatically gets their information and now compares it with those already written in the database, if no match is found, then the user is treated as a new one and is now assigned a new color and entry in the database, but if there was a match, then the system now recognizes this particular user as the one with the matching fingerprints.

As a warning, this authorization method is considered to be unsafe and unreliable, and it is recommended to use traditional methods for bigger projects, such as usernames/passwords, oauth, and so on.

Limitations
- Does not persist across incognito.
- Can be spoofed easily by modifying headers.
- Not GDPR-compliant for storing IP addresses without anonymization.

However, for this project, developed only for entertainment, this implementation is good enough and comes with a bonus in a way of not requiring any sort of password or account that users need to enter manually.

### Usage of local SQLite database

By using the sqlite3 library in Python, a lot of data can be stored in an SQL database, that includes user profiles and their prompts, which is what is done here. There are in total two tables - users and suggestions. The user table contains user_id (ID of the user), user_req (Encrypted user's fingerprints), and color (User's profile color). The suggestions table contains sug_id (ID of the prompt), user_id (ID of the user for the prompt), sug_text (Prompt itself), width (Width of the image), height (Height of the image), is_allowed (Status of the prompt, "Pending" if waits for the response from the admin, "True" if allowed, "False" if denied), timee (Time of user posting the prompt). These two tables have a 1-to-many relationship in the form of users(user_id) -> suggestions(user_id). This database is used almost constantly on the website and is the primary way of storing information on users and their prompts.

### Encryption of sensitive data

To still meet at least some means of privacy, encryption and anonymization of sensitive user information must implemented. So, as previously stated, the user's user-agent, IP address and also 'Accept-Language' from the headers of their browser are being kept in the local SQLite database, this is our sensitive data. This information is also anonymization at least somewhat and then encrypted using argon2's PasswordHasher from argon2-cffi library in Python. Anonymization is done by replacing the last 8 bits of the IP address with just plain zeros, making the precision of this data less significant. For example, this IP address won't show specific users in a household, but instead, provide information about the household network. As for encryption, argon2 in Python provides not only a good way to encrypt data with no way of decrypting it back but also provides a verification of the plain text if it matches the encrypted data. This doesn't raise an issue, because someone who wants to verify a specific encrypted text, still needs to know the text in plain format. And also, argon2 uses a random salt when encrypting text, so brute force is almost impossible, without spending close to an infinite amount of time.

### Communication between website and Stable Diffusion web UI API

To separate this project between two devices, one which only runs the website and the other which only runs the Stable Diffusion, I needed to create two Python files and connect them using the socket library. Before the website has started, a device with the receive_prompt.py (server which receives data from the website) should be up and running, as the website will connect to it immediately as it starts. The website, upon receiving a verdict from the admin on a specific prompt will send it over to the other device. That server, with receive_prompt.py, uses a queue to store prompts from the website in an organized way and goes one-by-one through them to send them to locally running Stable Diffusion web UI API. More information regarding the API itself is written on their GitHub repository right [here](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/API).

This communication is very simple and doesn't encrypt anything using argon2, as it must be in a plain format for Stable Diffusion to accept it. Information passed is a dictionary, containing the time of the user sending the prompt, the prompt itself, the width, and height of the image, and the color of the user's profile. This information (excluding color) is already shown to the admin before it is sent to a server, and regarding the color, it doesn't trace back to any information whatsoever besides the user's fingerprint in the database, which is already encrypted. So privacy is not an issue here.

### Flask-Session

While not as important as other parts, it is still being used in the website to keep some debug information (uuid, and user's profile color) in client and server cookie. That information is important for admin to keep track of the situation is something went completely wrong with some user. These Flask sessions are also used for separating user's experiences with one conflicting with the other. For this project, as it is for entertainment, cookie files are also used for an easter egg message. When the user was on the website before and is registered in the database, but for some reason lost their cookie files, a special message will be shown to them stating that they might be 'lost' and that they haven't lost their profile (color) because of only cookie files being removed.


### !More information regarding all of these points is provided in the comments in the code!

## Installation:

The application was tested and developed on Python 3.10, other versions were not tested.

It was also programmed and tested on Windows 11 (Stable Diffusion server) + Ubuntu (Website server), it is unknown if these Python apps will work with other operating systems.

Clone the repository on both servers from git clone: [https://github.com/ManulProgramming/server_with_stable_diffusion_api](https://github.com/ManulProgramming/server_with_stable_diffusion_api).

Go to the /Information_Theory_Encoding_Algorithms and install requirements using pip:

```bash
pip install -r requirements.txt
```

These requirements are only for the website server, as the other application receive_prompt.py for the Stable Diffusion server is in the folder /receive_prompts with its requirements being there.

## Usage:

Before running the website itself, using either a development server or production WSGI server, or Stable Diffusion server, you need to make some changes in the code and database. First of all, in both codes app.py and receive_prompts.py you need to change the HOST variable
```python
HOST = "IP_OF_YOUR_SERVER"
```

to the IP address of your second device which will run Stable Diffusion web UI, if it's on the same device then just set the variable to '127.0.0.1'. Next you need to run app.py once and it will show you the long error/instruction message what to do next. It was necessary to run it once, as it created a new file in the folder /database named data.db. You need to connect to this database and run a query to insert an admin account with their information, for example:
```sql
INSERT INTO users VALUES(0,"$argon2id$v=19$m=65536,t=3,p=4$YWa4mvcU/Rqfs04nEADyRw$eCsX4gEyx9kGXurniBTXElYsInIGFXs+svEyrhXA8Qk","white");
```

Replace the fingerprints and the color with those which you want to use. Remember that when writing the plain text for the fingerprint it should be in this format:
```
IP_ADDRESS_OF_ADMIN_WITH_LAST_8_BITS_BEING_JUST_0|ADMINS_USER_AGENT|ADMINS_ACCEPT_LANGUAGE_HEADER
```

For instance:
```
10.64.56.0|Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_9_8 rv:6.0; eu-ES) AppleWebKit/534.24.1 (KHTML, like Gecko) Version/4.0.1 Safari/534.24.1|en-US,en;q=1
```
Then encrypt it using argon2.

And the last thing you should do is to replace a secret key to whatever key you want in the app.py file:

```python
app.secret_key = 'YOUR_SECRET_KEY_HERE'
```

After that, you can run the receive_prompt.py or Stable Diffusion web UI API server on your device of choice by going into the folder /receive_prompt and running this command:
```bash
python receive_prompt.py
```

And then on the other device which will run website server you need to run this command in the root directory of the project:
```bash
python app.py
```

Or use the WSGI server of your choice to run it in the production server.

Website server will not start if the receive_prompts.py application is not running!

## Notes:

This application is created for entertainment purposes, and many problems, and limitations regarding scripts used here are stated in this README file. It should not be considered as a serious application, but rather as a basic Python project.

## License:

[MIT](https://github.com/ManulProgramming/server_with_stable_diffusion_api/blob/main/LICENSE)
