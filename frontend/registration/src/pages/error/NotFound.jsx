import { Link } from "react-router-dom";

const NotFound = () => (
  <div className="flex min-h-screen flex-col items-center justify-center text-center">
    <p className="text-6xl font-bold text-primary-500">404</p>
    <p className="mt-2 text-gray-500">The page you’re looking for doesn’t exist.</p>
    <Link to="/" className="btn-primary mt-6">Back to Home</Link>
  </div>
);

export default NotFound;
