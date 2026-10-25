# College Admission Website

A Streamlit college-information and admissions prototype with a separate static assistant interface served by the local Python API.

## Run in VS Code (Windows)

1. Open this folder in VS Code and open **Terminal → New Terminal**.
2. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install the project dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and set `GNANI_API_KEY` to your own valid key. Keep `.env` private and do not commit it. Alternatively, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and set the key in valid TOML syntax.
5. Start the college website:

   ```powershell
   python -m streamlit run app.py
   ```

The Streamlit website normally opens at `http://localhost:8501`. During local development, the app attempts to start `api.py` on port `8000`; the standalone text-to-speech assistant frontend is served at `http://localhost:8000`.

## Notes

- The project requires a valid Gnani API key at startup. The provided example files contain placeholders only.
- College, contact, achievements, fees, and seat data may be illustrative; verify institutional data before publishing.
- The visual update changes shared CSS and homepage presentation. The standalone chat's JavaScript event handlers and the website's existing page/business logic remain unchanged. `api.py`'s malformed duplicate startup wrapper was repaired so the existing API server can compile and launch.
