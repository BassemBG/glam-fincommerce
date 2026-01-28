"use client";
import React, { useState } from 'react';
import styles from './FloatingStylist.module.css';
import AIStylistAssistant from './AIStylistAssistant';

const FloatingStylist: React.FC = () => {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <>
            <button
                className={`${styles.orb} ${isOpen ? styles.orbOpen : ''}`}
                onClick={() => setIsOpen(true)}
                aria-label="Open AI Stylist"
            >
                <div className={styles.orbInner}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                </div>
                <div className={styles.pulse}></div>
            </button>

            <AIStylistAssistant
                isOpen={isOpen}
                onClose={() => setIsOpen(false)}
            />
        </>
    );
};

export default FloatingStylist;
