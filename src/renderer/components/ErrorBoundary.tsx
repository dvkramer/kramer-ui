import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallbackUI?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(_: Error): State {
    // Update state so the next render will show the fallback UI.
    return { hasError: true };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error in React component tree:", error, errorInfo);
    this.setState({ error, errorInfo });
    // You can also log the error to an error reporting service here
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallbackUI) {
        return this.props.fallbackUI;
      }
      return (
        <div className="p-4 m-4 bg-red-900 text-white rounded-lg text-center">
          <h1 className="text-2xl font-bold mb-2">Oops! Something went wrong.</h1>
          <p className="mb-2">An unexpected error occurred in the application.</p>
          <p className="text-sm mb-4">Please try refreshing the application or restarting it.</p>
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details className="mt-2 p-2 bg-red-800 rounded text-left text-xs">
              <summary>Error Details (Development Mode)</summary>
              <pre className="whitespace-pre-wrap mt-1">
                {this.state.error.toString()}
                {this.state.errorInfo && this.state.errorInfo.componentStack}
              </pre>
            </details>
          )}
           <button
            onClick={() => this.setState({ hasError: false, error: undefined, errorInfo: undefined })}
            className="mt-4 px-4 py-2 bg-red-700 hover:bg-red-600 rounded text-white"
           >
            Try to recover
           </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
