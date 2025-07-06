const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');

module.exports = (env, argv) => {
  const isProduction = argv.mode === 'production';
  const isDevelopment = !isProduction;

  const commonConfig = {
    mode: isProduction ? 'production' : 'development',
    devtool: isProduction ? false : 'source-map',
    resolve: {
      extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
    },
    module: {
      rules: [
        {
          test: /\.(ts|tsx)$/,
          exclude: /node_modules/,
          use: 'ts-loader',
        },
        {
          test: /\.css$/,
          use: ['style-loader', 'css-loader', 'postcss-loader'],
        },
      ],
    },
    watchOptions: {
      ignored: /node_modules|dist/,
    },
  };

const mainConfig = {
  ...commonConfig,
  entry: './src/main.ts',
  target: 'electron-main',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'main.js',
  },
  node: {
    __dirname: false, // Otherwise __dirname will be / instead of the real path
    __filename: false,
  },
};

const preloadConfig = {
  ...commonConfig,
  entry: './src/preload.ts', // Assuming you'll create src/preload.ts
  target: 'electron-preload',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'preload.js',
  },
};

const rendererConfig = {
  ...commonConfig,
  entry: './src/renderer/renderer.tsx',
  target: 'electron-renderer',
  output: {
    path: path.resolve(__dirname, 'dist', 'renderer'),
    filename: 'renderer.js',
    publicPath: '/', // Important for dev server and correct asset pathing
  },
  devServer: {
    port: 8080,
    hot: true,
    static: {
      directory: path.resolve(__dirname, 'dist', 'renderer'),
      publicPath: '/',
    },
    headers: {
      'Access-Control-Allow-Origin': '*', // Optional: Useful for some HMR setups or if fetching from other local services
    },
    historyApiFallback: true, // For single-page applications
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: './index.html', // Your HTML template file
      filename: 'index.html', // Output filename in dist/renderer/
      // publicPath is not strictly needed here if output.publicPath is set and devServer serves correctly
    }),
    // If you have static assets like images or fonts in a public/static folder
    // new CopyWebpackPlugin({
    //   patterns: [
    //     { from: path.resolve(__dirname, 'public/static'), to: 'static' },
    //   ],
    // }),
  ],
};

  const configs = [];
  if (env && env.target) {
    if (env.target.includes('main')) {
      configs.push(mainConfig);
    }
    if (env.target.includes('preload')) {
      configs.push(preloadConfig);
    }
    if (env.target.includes('renderer')) {
      configs.push(rendererConfig);
    }
  } else {
    // Default to all if no target specified
    configs.push(mainConfig, preloadConfig, rendererConfig);
  }
  return configs;
};
