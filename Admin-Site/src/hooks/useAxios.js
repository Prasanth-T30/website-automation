import { useCallback, useState } from "react";

/**
 * Generic wrapper around an async API call, exposing loading/error state
 * without needing a data-fetching library.
 */
export const useAxios = (requestFn) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const execute = useCallback(
    async (...args) => {
      setLoading(true);
      setError(null);
      try {
        const result = await requestFn(...args);
        setData(result);
        return result;
      } catch (err) {
        const message = err?.response?.data?.message || err?.response?.data?.detail || err.message;
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [requestFn]
  );

  return { execute, loading, error, data };
};
