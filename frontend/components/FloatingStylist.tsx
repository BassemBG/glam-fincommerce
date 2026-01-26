"use client";

import React, { useState, useEffect } from 'react';
import styles from './FloatingStylist.module.css';
import TryOnVisualizer from './TryOnVisualizer';
import { API } from '../lib/api';
import { authFetch } from '../lib/auth';
import { useAuthGuard } from '../lib/useAuthGuard';
import { WalletConfirmationModal } from './WalletConfirmationModal';

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
    const [stagedFile, setStagedFile] = useState<File | null>(null);
    const [stagedPreview, setStagedPreview] = useState<string | null>(null);
    const [user, setUser] = useState<any>(null);
    const [walletModalData, setWalletModalData] = useState<{
        isOpen: boolean;
        itemName: string;
        price: number;
        currency: string;
        balance: number;
    }>({
        isOpen: false,
        itemName: '',
        price: 0,
        currency: 'TND',
        balance: 0
    });

    // Simple markdown renderer for links [text](url) and bold **text**
    const renderMarkdown = (content: string) => {
        if (!content) return null;

        // Match ![description](url) - Images first to avoid overlap with links
        const imageRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
        // Match [text](url) - Links
        const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
        // Match **text**
        const boldRegex = /\*\*([^*]+)\*\*/g;

        let parts: (string | React.ReactNode)[] = [content];

        // Replace bold
        parts = parts.flatMap((part): (string | React.ReactNode)[] => {
            if (typeof part !== 'string') return [part];
            const bits = part.split(boldRegex);
            return bits.map((bit, i) => i % 2 === 1 ? <strong key={`b-${i}`}>{bit}</strong> : bit);
        });

        // Replace images
        parts = parts.flatMap(part => {
            if (typeof part !== 'string') return [part];
            const bits = part.split(imageRegex);
            const elements: (string | React.ReactNode)[] = [];
            for (let i = 0; i < bits.length; i += 3) {
                elements.push(bits[i]);
                if (bits[i + 1] !== undefined) {
                    elements.push(
                        <div key={`img-container-${i}`} className={styles.renderedImageContainer}>
                            <img
                                key={`img-${i}`}
                                src={bits[i + 2]}
                                alt={bits[i + 1] || 'Embedded image'}
                                className={styles.renderedImage}
                            />
                        </div>
                    );
                }
            }
            return elements;
        });

        // Replace links
        parts = parts.flatMap(part => {
            if (typeof part !== 'string') return [part];
            const bits = part.split(linkRegex);
            const elements: (string | React.ReactNode)[] = [];
            for (let i = 0; i < bits.length; i += 3) {
                elements.push(bits[i]);
                if (bits[i + 1] !== undefined) {
                    elements.push(
                        <a
                            key={`l-${i}`}
                            href={bits[i + 2]}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: '#22c55e', textDecoration: 'underline' }}
                        >
                            {bits[i + 1]}
                        </a>
                    );
                }
            }
            return elements;
        });

        return parts;
    };

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
                    setUser(data);
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

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            setStagedFile(file);
            setStagedPreview(URL.createObjectURL(file));
        }
    };

    const removeStagedImage = () => {
        setStagedFile(null);
        setStagedPreview(null);
    };

    const sendMessage = async () => {
        if (!input.trim() && !stagedFile) return;

        const userMsg = {
            role: 'user',
            text: input,
            image: stagedPreview
        };

        setMessages([...messages, userMsg]);
        const currentInput = input;
        const currentFile = stagedFile;

        setInput('');
        removeStagedImage();
        setIsLoading(true);

        const formData = new FormData();
        formData.append('message', currentInput);
        if (currentFile) {
            formData.append('file', currentFile);
        }

        // Convert history for backend
        const historyJSON = JSON.stringify(messages.map(m => ({
            role: m.role,
            content: m.text
        })));
        formData.append('history', historyJSON);

        try {
            const res = await authFetch(API.stylist.chat, {
                method: 'POST',
                body: formData
            });

            if (res.ok) {
                const botResponse = await res.json();
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    text: botResponse.response,
                    images: botResponse.images,
                    suggested_outfits: botResponse.suggested_outfits
                }]);

                // Check for wallet confirmation signal
                // 1. Structured JSON (Preferred)
                if (botResponse.wallet_confirmation?.required) {
                    const wc = botResponse.wallet_confirmation;
                    setWalletModalData({
                        isOpen: true,
                        itemName: wc.item_name,
                        price: wc.price,
                        currency: wc.currency,
                        balance: wc.current_balance
                    });
                }
                // 2. Regex Fallback (Legacy)
                else {
                    const walletSignal = botResponse.response.match(/\[WALLET_CONFIRMATION_REQUIRED\] item='([^']+)' price=([\d.]+) currency='([^']+)' balance=([\d.]+)/);
                    if (walletSignal) {
                        setWalletModalData({
                            isOpen: true,
                            itemName: walletSignal[1],
                            price: parseFloat(walletSignal[2]),
                            currency: walletSignal[3],
                            balance: parseFloat(walletSignal[4])
                        });
                    }
                }
            } else {
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    text: "I'm having trouble connecting to my fashion brain right now. Try again?"
                }]);
            }
        } catch (err) {
            console.error("Chat error:", err);
        } finally {
            setIsLoading(false);
        }
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
                                {user?.wallet_balance !== undefined ? (
                                    <span className={styles.budgetBadge}>
                                        Balance: {user.wallet_balance} {user.currency || 'TND'}
                                    </span>
                                ) : user?.budget_limit && (
                                    <span className={styles.budgetBadge}>
                                        Budget: {user.budget_limit} {user.currency || 'TND'}
                                    </span>
                                )}
                            </div>
                            <button className={styles.closeBtn} onClick={() => setIsOpen(false)}>✕</button>
                        </div>

                        <div className={styles.chatBody}>
                            {messages.map((msg, i) => (
                                <div key={i} className={`${styles.message} ${styles[msg.role]}`}>
                                    <div className={styles.bubble}>
                                        {msg.image && (
                                            <img src={msg.image} alt="User upload" className={styles.userUploadPreview} />
                                        )}
                                        <div className={styles.textContent}>
                                            {renderMarkdown(msg.text)}
                                        </div>

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
                            {stagedPreview && (
                                <div className={styles.stagedArea}>
                                    <div className={styles.stagedPreview}>
                                        <img src={stagedPreview} alt="Staged" />
                                        <button onClick={removeStagedImage} className={styles.removeStaged}>✕</button>
                                    </div>
                                </div>
                            )}
                            <div className={styles.inputRow}>
                                <label className={styles.uploadToggle}>
                                    <input type="file" accept="image/*" onChange={handleFileChange} hidden />
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 22H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h3.17l1.83-3h6l1.83 3H21a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2z" /><circle cx="12" cy="13" r="4" /></svg>
                                </label>
                                <input
                                    type="text"
                                    placeholder="Ask Glam anything..."
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                                />
                                <button onClick={sendMessage} className={styles.sendBtn} disabled={isLoading}>
                                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
                                </button>
                            </div>
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

            <WalletConfirmationModal
                isOpen={walletModalData.isOpen}
                onClose={() => setWalletModalData(prev => ({ ...prev, isOpen: false }))}
                itemName={walletModalData.itemName}
                price={walletModalData.price}
                currency={walletModalData.currency}
                balance={walletModalData.balance}
                onSuccess={(newBalance) => {
                    setUser((prev: any) => prev ? { ...prev, wallet_balance: newBalance } : prev);
                    setMessages(prev => [...prev, {
                        role: 'assistant',
                        text: `Great! I've updated your wallet. Your new balance is **${newBalance} ${walletModalData.currency}**. I've added these items to your purchase history!`
                    }]);
                }}
            />
        </>
    );
};

export default FloatingStylist;
