import { useCallback, useEffect, useState } from "react";
import { get } from "./api";

export interface ApiState<T> {
  data: T | null;
  error: string | null;
  reload: () => void;
}

export function useApi<T>(path: string, pollMs = 0): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => {
    setVersion((v) => v + 1);
  }, []);

  useEffect(() => {
    let live = true;
    const load = () => {
      get<T>(path)
        .then((value) => {
          if (live) {
            setData(value);
            setError(null);
          }
        })
        .catch((e: unknown) => {
          if (live) setError(String(e));
        });
    };
    load();
    const timer = pollMs > 0 ? setInterval(load, pollMs) : undefined;
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [path, pollMs, version]);

  return { data, error, reload };
}
