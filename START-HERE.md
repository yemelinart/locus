# Welcome to Locus

[Русский](START-HERE.ru.md) · [Product overview](README.md)

Locus is a local web application. It runs on your own computer and opens in your browser. A link beginning with `127.0.0.1` points to your own machine: sending that link to a friend will not give them your app or your research.

## Before the first launch

- Use a Mac with enough memory for your chosen local model. A dedicated 8 GB profile has not been validated.
- Install Python 3.11–3.14 (3.12 recommended) from [python.org](https://www.python.org/downloads/) and Node.js 22.12+ or a supported newer version from [nodejs.org](https://nodejs.org/en/download). npm comes with Node.js. If you already use `uv`, setup can create the Python 3.12 environment with it.
- Install [LM Studio](https://lmstudio.ai/) or [Ollama](https://ollama.com/), download a chat model and start its local server. Models are separate downloads and may be large.
- Extract the whole Locus ZIP to a permanent folder, for example `~/Applications/Locus`. Keep all files together.

## Launch

Double-click **Start Locus.command**. The first run downloads Python and frontend dependencies and builds the app; subsequent launches reuse the installed environment. A Terminal window hosts the local server and your browser opens at http://127.0.0.1:8420.

If macOS declines to open a downloaded command file, consult System Settings → Privacy & Security and review its origin. This alpha is not signed or notarised. Do not disable macOS security globally.

You can also open Terminal in the extracted Locus folder and run:

```sh
sh scripts/setup.sh
sh scripts/start.sh
```

Keep the terminal open. To stop, pause any running research and press Control-C in that terminal. Progress stays in `data/`; interrupted research is recovered paused, never automatically resumed.

## Connect the model

In Settings → Local AI select your provider and address:

| Provider | Default address |
| --- | --- |
| LM Studio | `http://127.0.0.1:1234/v1` |
| Ollama | `http://127.0.0.1:11434` |
| Compatible local server | Use its actual address, often `http://127.0.0.1:8080/v1` |

Refresh models, choose a chat model and save. Start with recommended generation settings. Then check Settings → Web search. The in-app **About & guide** explains the first search and how to interpret results.

## If something goes wrong

- **Python or Node.js missing:** install the versions above, close and reopen Terminal, then launch again.
- **No models appear:** check that the provider is running, its server is enabled and a local chat model has been downloaded. Verify the address.
- **Model too large / context too long:** choose a smaller model, reduce its context in the provider and reduce the page excerpt in Locus settings. More memory or a different model may be needed.
- **Search unavailable:** check internet access and search-engine availability in Settings. A free provider may temporarily block or limit requests.
- **Browser page will not open:** check the server terminal for an error. Opening `frontend/index.html` directly does not run Locus.
- **Port 8420 belongs to something else:** from Terminal use `LOCUS_PORT=8422 sh scripts/start.sh`, then open http://127.0.0.1:8422.

## Update without losing research

There is no automatic updater yet. Pause research, stop the server and back up the whole `data/` folder. Extract a newer release to a new folder, copy your `data/` backup into it, then run setup and start from the new folder. Keep the old folder until the new version is verified. Do not copy `.venv/` or `node_modules/` between installations. Do not open a newer database with an older app version; restore the matching backup instead.

If you use Git, you can pull an update in the existing checkout and rerun setup after backing up data and stopping the server.

## Give a copy to a friend

Send the clean application ZIP, or invite their GitHub account to the private repository. They follow this guide on their computer and use their own model. An exported **research ZIP** is a different file: it contains results, not the application. Details: [Sharing](docs/SHARING.md).
