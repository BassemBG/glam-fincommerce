"use client";

import { useState, useRef, useEffect } from 'react';
import styles from './page.module.css';
import { useAuthGuard } from '../../lib/useAuthGuard';

export default function StylistChat() {
    useAuthGuard();
    const [messages, setMessages] = useState([
        { role: 'assistant', text: "Hi! I'm Glam, your personal stylist. What are we planning for today? A date, work, or just a chic casual look?" },
    ]);
    const [input, setInput] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = () => {
        if (!input.trim()) return;

        setMessages([...messages, { role: 'user', text: input }]);
        setInput('');

        // Simulate AI response
        setTimeout(() => {
            setMessages(prev => [...prev, { role: 'assistant', text: "That sounds exciting! Let me look through your closet for the perfect pieces..." }]);
        }, 1000);
    };

    return (
        <div className={styles.chatContainer}>
            <header className={styles.header}>
                <h1>Stylist Glam</h1>
            </header>

            <div className={styles.messageList}>
                {messages.map((msg, i) => (
                    <div key={i} className={`${styles.message} ${msg.role === 'user' ? styles.user : styles.assistant}`}>
                        <div className={styles.bubble}>
                            {msg.text}
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            <div className={styles.inputArea}>
                <input
                    type="text"
                    placeholder="Ask Glam anything..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                    className={styles.input}
                />
                <button onClick={handleSend} className={styles.sendBtn}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polyline points="22 2 15 22 11 13 2 9 22 2" /></svg>
                </button>
            </div>
        </div>
    );
}
