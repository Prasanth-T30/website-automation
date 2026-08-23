import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";
export default function NotFound() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-3 px-6 text-center">
      <p className="brand-gradient-text text-5xl font-extrabold">404</p>
      <h1 className="text-lg font-bold text-fg">This page does not exist</h1>
      <p className="max-w-sm text-sm text-fg-muted">
        The link may be out of date, or the screen may not be built yet.
      </p>
      <Button className="mt-2" onClick={() => window.history.back()}>
        Go back
      </Button>
      <Link to="/" className="text-xs font-semibold text-[var(--brand-text)] hover:underline">
        Return to the dashboard
      </Link>
    </div>
  );
}
