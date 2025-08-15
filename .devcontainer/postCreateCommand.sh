git config --global core.autocrlf input

mkdir -p ~/.streamlit
cat > ~/.streamlit/credentials.toml <<HERE
[general]
    email = "noreply@example.com"
[browser]
    gatherUsageStats = false
HERE
