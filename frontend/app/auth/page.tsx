import Link from "next/link";
import styles from "./auth.module.css";

export default function AuthIndex() {
  return (
    <div className={styles.shell}>
      <div className={styles.hero}>AI Virtual Closet</div>
      <div className={styles.card}>
        <div className={styles.headerRow}>
          <div>
            <p className={styles.eyebrow}>Choose Access</p>
            <h1>Sign in or sign up</h1>
            <p className={styles.muted}>Select the account type that fits you.</p>
          </div>
        </div>

        <div className={styles.choiceGrid}>
          <div className={styles.choiceCard}>
            <h2>User</h2>
            <p>Access your closet, outfits, and AI stylist.</p>
            <div className={styles.choiceButtons}>
              <Link className={styles.primaryBtn} href="/auth/login">Sign In</Link>
              <Link className={styles.secondaryBtn} href="/auth/signup">Sign Up</Link>
            </div>
          </div>

          <div className={styles.choiceCard}>
            <h2>Brand</h2>
            <p>Manage brand ingestion and profile data.</p>
            <div className={styles.choiceButtons}>
              <Link className={styles.primaryBtn} href="/auth/brand/login">Sign In</Link>
              <Link className={styles.secondaryBtn} href="/auth/brand/signup">Sign Up</Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
