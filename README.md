# 🏋️‍♂️ CrossFit WOD Telegram Bot

![CrossFit Logo]([https://i.imgur.com/pXugrn6.png](https://www.kisacoresearch.com/sites/default/files/logos/crossfit-llc-logo.png))

This project automatically fetches the Workout of the Day (WOD) from a CrossFit website and posts it to a Telegram channel.

## 📋 Features

- 🕒 Runs every 5 minutes via GitHub Actions
- 🌐 Fetches the latest WOD from [CrossFit Panda](https://wods.crossfitpanda.com/)
- 📱 Posts formatted workouts to a Telegram channel
- 🔄 Avoids duplicate posts by tracking the last sent date

## 🛠️ Technologies Used

- Python 3
- BeautifulSoup4 for web scraping
- Requests library for HTTP requests
- GitHub Actions for scheduling

## 🚀 Setup

1. Clone this repository
2. Set up a Telegram bot and channel
3. Add your Telegram Bot API Token as a GitHub secret named `TELEGRAM_API_TOKEN`
4. Modify the `TELEGRAM_CHANNEL_ID` in the script to match your channel
5. Push the changes to GitHub

GitHub Actions will automatically run the script every 5 minutes.

## 📊 Sample Output

Here's how the formatted message looks in Telegram:

![Sample Telegram Message](https://i.imgur.com/XyZ1234.png)

## 📈 Future Improvements

- [ ] Add user customization for workout preferences
- [ ] Implement error handling and notifications
- [ ] Create a web interface for easy configuration

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check [issues page](https://github.com/yourusername/your-repo-name/issues).

## 📜 License

This project is [MIT](https://choosealicense.com/licenses/mit/) licensed.

---

Made with ❤️ by [LIRAN]
