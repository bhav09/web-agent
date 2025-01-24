# Base image with Python
FROM python:3.11.8

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install dependencies
RUN pip install -r requirements.txt

# Install Playwright and its browser dependencies
RUN playwright install --with-deps

# Copy the entire application code to the container
COPY . /app/

# Expose the port Streamlit runs on
EXPOSE 8080

# Command to run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
