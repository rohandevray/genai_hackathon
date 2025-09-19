import { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import styles from "./AuthForm.module.css";

const API = "http://localhost:8000";

export default function AuthForm() {
  const [isLogin, setIsLogin] = useState(true);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const payload = isLogin
        ? { email, password }
        : { name, email, password };

      const res = await axios.post(
        isLogin ? `${API}/login` : `${API}/signup`,
        payload,
        { headers: { "Content-Type": "application/json" } }
      );

      if (isLogin) {
        localStorage.setItem("authToken", res.data.access_token);
        localStorage.setItem("username", res.data.usernames);
        console.log(res.data);
        toast.success("Login successful!");
        navigate("/"); // Redirect to Home
      } else {
        toast.success(res.data.msg || "Signup successful! Please login.");
        setIsLogin(true);
      }

      setName("");
      setEmail("");
      setPassword("");
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(
        detail
          ? Array.isArray(detail)
            ? detail.map(d => `${d.loc[1]}: ${d.msg}`).join(", ")
            : detail
          : "Something went wrong!"
      );
    }
  };

  return (
    <div className={styles.authContainer}>
      <div className={styles.authCard}>
        <h2>{isLogin ? "Login" : "Sign Up"}</h2>

        <form onSubmit={handleSubmit}>
          {!isLogin && (
            <input
              type="text"
              placeholder="Full Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required={!isLogin}
            />
          )}

          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <button type="submit" className={styles.authBtn}>
            {isLogin ? "Login" : "Sign Up"}
          </button>
        </form>

        <p className={styles.authToggle}>
          {isLogin ? "Don’t have an account?" : "Already have an account?"}{" "}
          <button onClick={() => setIsLogin(!isLogin)}>
            {isLogin ? "Sign Up" : "Login"}
          </button>
        </p>
      </div>
    </div>
  );
}
