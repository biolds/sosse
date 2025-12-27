"use client";

import { createContext, useContext, useState } from "react";

interface FloatContextType {
  loading: boolean;
  setLoading: (value: boolean) => void;
}

const FloatContext = createContext<FloatContextType>({
  loading: false,
  setLoading: () => {},
});

export const FloatProvider = ({ children }: { children: React.ReactNode }) => {
  const [loading, setLoading] = useState(false);

  return (
    <FloatContext.Provider value={{ loading, setLoading }}>
      {children}
    </FloatContext.Provider>
  );
};

export const useFloat = () => useContext(FloatContext);
