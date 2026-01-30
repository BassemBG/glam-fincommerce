"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { authFetch } from '../lib/auth';
import { API } from '../lib/api';
import styles from './FloatingProfileButton.module.css';

const FloatingProfileButton = () => {
    const pathname = usePathname();
    const [userPhoto, setUserPhoto] = useState<string | null>(null);

    useEffect(() => {
        const fetchUser = async () => {
            try {
                const res = await authFetch(API.users.me);
                if (res.ok) {
                    const data = await res.json();
                    setUserPhoto(data.full_body_image);
                }
            } catch (err) {
                console.error("Failed to fetch user photo", err);
            }
        };
        fetchUser();
    }, []);

    // Don't show on settings page or auth pages
    if (pathname === '/settings' || pathname.startsWith('/auth')) return null;

    return (
        <Link href="/settings" className={styles.floatingBtn} aria-label="My Profile">
            {userPhoto ? (
                <img src={userPhoto} alt="Me" className={styles.avatar} />
            ) : (
                <div className={styles.placeholder}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
                </div>
            )}
        </Link>
    );
};

export default FloatingProfileButton;
