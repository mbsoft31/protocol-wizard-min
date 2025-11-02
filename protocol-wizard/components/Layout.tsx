
import React from 'react';
import ApiKeyInput from './ApiKeyInput';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {children}
      <footer className="mt-8 text-center text-slate-500">
        <ApiKeyInput />
        <p className="mt-4 text-sm">Protocol Wizard | Built with React & Gemini</p>
      </footer>
    </div>
  );
};

export default Layout;
