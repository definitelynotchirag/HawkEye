# Log Streaming Application Frontend

This project is a frontend application built with React that streams log data from a Python backend. It provides a user-friendly interface to visualize and monitor log entries in real-time.

## Project Structure

- **public/**: Contains static files for the frontend application.
  - **index.html**: The main HTML file that serves as the entry point for the React application.
  - **favicon.svg**: The favicon for the application.

- **src/**: Contains the source code for the React application.
  - **App.js**: The main component that sets up routing and renders the application layout.
  - **components/**: Contains reusable components for the application.
    - **Dashboard.js**: Displays the overall status and log stream.
    - **LogEntry.js**: Represents a single log entry in the log stream.
    - **LogStream.js**: Handles the real-time streaming of log data from the backend.
    - **StatusIndicator.js**: Visually indicates the status of the log entries.
  - **hooks/**: Contains custom hooks for managing application state.
    - **useLogStream.js**: Manages the connection to the log stream and provides log data to components.
  - **index.js**: The entry point for the React application, rendering the App component into the DOM.
  - **utils/**: Contains utility functions for formatting log data.
    - **formatters.js**: Exports functions for formatting log data for display.

## Setup Instructions

1. **Clone the repository**:
   ```
   git clone <repository-url>
   cd log-streaming-app/frontend
   ```

2. **Install dependencies**:
   ```
   npm install
   ```

3. **Run the application**:
   ```
   npm start
   ```

The application will be available at `http://localhost:3000`.

## Usage

Once the application is running, it will connect to the backend service and start streaming log data. The Dashboard component will display the log entries in real-time, and you can monitor the status of each log entry through the StatusIndicator component.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License.