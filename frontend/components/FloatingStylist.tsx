"use client";

import { useState, useEffect } from 'react';
import styles from './FloatingStylist.module.css';
import TryOnVisualizer from './TryOnVisualizer';
import { API } from '../lib/api';
import { authFetch } from '../lib/auth';
import { useAuthGuard } from '../lib/useAuthGuard';

const FloatingStylist = () => {
    const token = useAuthGuard();
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<any[]>([
        { role: 'assistant', text: "Hello! I'm your AI Stylist. How can I help you dress today?" }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [tryOnData, setTryOnData] = useState<any>(null);
    const [userPhoto, setUserPhoto] = useState<string | null>(null);
    const [hasItems, setHasItems] = useState(false);

    useEffect(() => {
        if (!token) return; // Don't fetch if no token
        
        const fetchData = async () => {
            try {
                const [userRes, itemsRes] = await Promise.all([
                    authFetch(API.users.me),
                    authFetch(API.closet.items)
                ]);

                if (userRes.ok) {
                    const data = await userRes.json();
                    setUserPhoto(data.full_body_image);
                }

                if (itemsRes.ok) {
                    const items = await itemsRes.json();
                    setHasItems(items.length > 0);
                }
            } catch (err) {
                console.error("Failed to fetch:", err);
            }
        };
        fetchData();
    }, [token]);

    // Don't render if closet is empty
    if (!hasItems) return null;

    const sendMessage = () => {
        if (!input.trim()) return;
        const userMsg = { role: 'user', text: input };
        setMessages([...messages, userMsg]);
        setInput('');
        setIsLoading(true);

        // Mocking the Backend response structure we just defined
        setTimeout(() => {
            const botResponse = {
                role: 'assistant',
                text: "I've curated some fresh looks for your request! These pieces from your closet would work perfectly together.",
                images: [
                    "https://images.unsplash.com/photo-1564584217132-2271feaeb3c5?w=200", // Cream Silk Blouse
                    "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=200"  // Gold heels
                ],
                suggested_outfits: [
                    { name: "Golden Hour Glow", score: 9.8 }
                ]
            };
            setMessages(prev => [...prev, botResponse]);
            setIsLoading(false);
        }, 1500);
    };

    return (
        <>
            <button
                className={`${styles.orb} ${isOpen ? styles.orbOpen : ''}`}
                onClick={() => setIsOpen(!isOpen)}
                aria-label="Open AI Stylist"
            >
                <div className={styles.orbInner}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                </div>
                <div className={styles.pulse}></div>
            </button>

            {isOpen && (
                <div className={styles.drawerOverlay} onClick={() => setIsOpen(false)}>
                    <div className={styles.drawer} onClick={e => e.stopPropagation()}>
                        <div className={styles.drawerHeader}>
                            <div className={styles.headerTitle}>
                                <div className={styles.statusDot}></div>
                                <h3>AI Stylist</h3>
                            </div>
                            <button className={styles.closeBtn} onClick={() => setIsOpen(false)}>✕</button>
                        </div>

                        <div className={styles.chatBody}>
                            {messages.map((msg, i) => (
                                <div key={i} className={`${styles.message} ${styles[msg.role]}`}>
                                    <div className={styles.bubble}>
                                        {msg.text}

                                        {msg.images && (
                                            <div className={styles.imageGrid}>
                                                {msg.images.map((img: string, idx: number) => (
                                                    <img key={idx} src={img} alt="Closet Item" className={styles.chatImg} />
                                                ))}
                                            </div>
                                        )}

                                        {msg.suggested_outfits && (
                                            <div className={styles.outfitStack}>
                                                {msg.suggested_outfits.map((fit: any, idx: number) => (
                                                    <div
                                                        key={idx}
                                                        className={styles.fitBadge}
                                                        onClick={() => userPhoto && setTryOnData({ items: fit.item_details || [] })}
                                                    >
                                                        ✨ {fit.name} ({fit.score}/10)
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                            {isLoading && (
                                <div className={`${styles.message} ${styles.assistant}`}>
                                    <div className={styles.typing}>•••</div>
                                </div>
                            )}
                        </div>

                        <div className={styles.chatFooter}>
                            <input
                                type="text"
                                placeholder="Ask your stylist..."
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                            />
                            <button onClick={sendMessage} className={styles.sendBtn}>
                                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {tryOnData && userPhoto && (
                <TryOnVisualizer
                    bodyImage={userPhoto}
                    items={tryOnData.items}
                    onClose={() => setTryOnData(null)}
                />
            )}
        </>
    );
};

export default FloatingStylist;
