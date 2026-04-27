import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider locale={ruRU}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>
);
