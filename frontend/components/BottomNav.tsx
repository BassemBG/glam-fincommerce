"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import styles from './BottomNav.module.css';
import { getRole } from '../lib/auth';

interface NavItem {
    href: string;
    label: string;
    icon: React.ReactNode;
    isUpload?: boolean;
}

const BottomNav = () => {
    const pathname = usePathname();
    const [role, setRole] = useState<"user" | "brand" | null>(null);

    useEffect(() => {
        setRole(getRole());
    }, []);

    const isBrand = role === "brand";

    const userNavItems: NavItem[] = [
        { href: '/', label: 'Closet', icon: <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" /></svg> },
        { href: '/outfits', label: 'Outfits', icon: <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" /><path d="M7 3v18" /><path d="M17 3v18" /><path d="M3 12h18" /></svg> },
        { href: '/upload', label: 'Upload', isUpload: true, icon: <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg> },
        { href: '/advisor', label: 'Advisor', icon: <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg> },
        { href: '/brands', label: 'Shop', icon: <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" /><path d="M3 6h18" /><path d="M16 10a4 4 0 0 1-8 0" /></svg> }
    ];

    const brandNavItems: NavItem[] = [
        { href: '/advisor/brands', label: 'Ingestion', icon: <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2" /><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" /></svg> },
        { href: '/advisor/brands/profile', label: 'Profile', icon: <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg> }
    ];

    const navItems = isBrand ? brandNavItems : userNavItems;

    return (
        <nav className={styles.bottomNav}>
            {navItems.map((item) => (
                <Link
                    key={item.href}
                    href={item.href}
                    className={`${styles.navItem} ${pathname === item.href ? styles.navItemActive : ''}`}
                >
                    {item.isUpload ? (
                        <div className={styles.uploadBtn}>
                            {item.icon}
                        </div>
                    ) : (
                        <div className={styles.iconWrapper}>
                            {item.icon}
                        </div>
                    )}
                    {!item.isUpload && <span>{item.label}</span>}
                </Link>
            ))}
        </nav>
    );
};

export default BottomNav;
