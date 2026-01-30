"use client";
import React, { useState, useEffect } from 'react';
import styles from './FloatingStylist.module.css';
import TryOnVisualizer from './TryOnVisualizer';
import { API } from '../lib/api';
import { authFetch } from '../lib/auth';
import { useAuthGuard } from '../lib/useAuthGuard';
import { WalletConfirmationModal } from './WalletConfirmationModal';

interface AIStylistAssistantProps {
    isOpen: boolean;
    onClose: () => void;
}

// Suggested prompts for quick actions
const SUGGESTED_PROMPTS = [
    { icon: '☀️', text: 'Show me casual outfits for summer', category: 'outfits' },
    { icon: '🛍️', text: 'What brands match my style?', category: 'shopping' },
    { icon: '👔', text: 'Help me organize my closet', category: 'closet' },
    { icon: '💰', text: 'Find affordable options for me', category: 'budget' },
    { icon: '🎨', text: 'What colors look good on me?', category: 'style' },
    { icon: '🌟', text: 'Create an outfit for a special event', category: 'occasion' }
];

// Smart follow-up suggestions based on context
const getSmartFollowUps = (lastMessage: string, messageHistory: any[]) => {
    const lowercaseMsg = lastMessage.toLowerCase();

    // Brand search follow-ups
    if (lowercaseMsg.includes('brand') || lowercaseMsg.includes('shop') || lowercaseMsg.includes('buy')) {
        return [
            { icon: '💸', text: 'Show me items under my budget' },
            { icon: '🎯', text: 'Filter by specific brands' },
            { icon: '⭐', text: 'What are the best rated items?' }
        ];
    }

    // Outfit creation follow-ups
    if (lowercaseMsg.includes('outfit') || lowercaseMsg.includes('wear') || lowercaseMsg.includes('style')) {
        return [
            { icon: '👗', text: 'Try this outfit on me' },
            { icon: '🔄', text: 'Show me more outfit ideas' },
            { icon: '📸', text: 'Save this outfit to my collection' }
        ];
    }

    // Closet organization follow-ups
    if (lowercaseMsg.includes('closet') || lowercaseMsg.includes('wardrobe') || lowercaseMsg.includes('organize')) {
        return [
            { icon: '📤', text: 'Upload more clothing items' },
            { icon: '🏷️', text: 'Categorize my items better' },
            { icon: '🗑️', text: 'Find items I never wear' }
        ];
    }

    // Color/style analysis follow-ups
    if (lowercaseMsg.includes('color') || lowercaseMsg.includes('vibe') || lowercaseMsg.includes('aesthetic')) {
        return [
            { icon: '🎨', text: 'Update my style preferences' },
            { icon: '🌈', text: 'Show items in my color palette' },
            { icon: '✨', text: 'Suggest new styles for me' }
        ];
    }

    // Default follow-ups
    return [
        { icon: '🛍️', text: 'Browse shopping recommendations' },
        { icon: '👔', text: 'Create a new outfit' },
        { icon: '📊', text: 'View my style profile' }
    ];
};

const AIStylistAssistant = ({ isOpen, onClose }: AIStylistAssistantProps) => {
    const token = useAuthGuard();
    const [messages, setMessages] = useState<any[]>([
        { role: 'assistant', text: "Hello! I'm your AI Stylist. How can I help you dress today?" }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [showSuggestions, setShowSuggestions] = useState(true);
    const [smartFollowUps, setSmartFollowUps] = useState<any[]>([]);
    const [typingAgent, setTypingAgent] = useState<string>('')
    const [tryOnData, setTryOnData] = useState<any>(null);
    const [userPhoto, setUserPhoto] = useState<string | null>(null);
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

    const renderMarkdown = (content: string) => {
        if (!content) return null;
        const imageRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
        const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
        const boldRegex = /\*\*([^*]+)\*\*/g;
        let parts: (string | React.ReactNode)[] = [content];
        parts = parts.flatMap((part): (string | React.ReactNode)[] => {
            if (typeof part !== 'string') return [part];
            const bits = part.split(boldRegex);
            return bits.map((bit, i) => i % 2 === 1 ? <strong key={`b-${i}`}>{bit}</strong> : bit);
        });
        parts = parts.flatMap(part => {
            if (typeof part !== 'string') return [part];
            const bits = part.split(imageRegex);
            const elements: (string | React.ReactNode)[] = [];
            for (let i = 0; i < bits.length; i += 3) {
                elements.push(bits[i]);
                if (bits[i + 1] !== undefined) {
                    elements.push(
                        <div key={`img-container-${i}`} className={styles.renderedImageContainer}>
                            <img src={bits[i + 2]} alt={bits[i + 1] || 'Embedded image'} className={styles.renderedImage} />
                        </div>
                    );
                }
            }
            return elements;
        });
        parts = parts.flatMap(part => {
            if (typeof part !== 'string') return [part];
            const bits = part.split(linkRegex);
            const elements: (string | React.ReactNode)[] = [];
            for (let i = 0; i < bits.length; i += 3) {
                elements.push(bits[i]);
                if (bits[i + 1] !== undefined) {
                    elements.push(
                        <a key={`l-${i}`} href={bits[i + 2]} target="_blank" rel="noopener noreferrer" style={{ color: '#22c55e', textDecoration: 'underline' }}>
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
        if (!token || !isOpen) return;
        const fetchData = async () => {
            try {
                const userRes = await authFetch(API.users.me);
                if (userRes.ok) {
                    const data = await userRes.json();
                    setUserPhoto(data.full_body_image);
                    setUser(data);
                }
            } catch (err) { console.error("Failed to fetch user:", err); }
        };
        fetchData();
    }, [token, isOpen]);

    const [stagedFile, setStagedFile] = useState<File | null>(null);
    const [stagedPreview, setStagedPreview] = useState<string | null>(null);

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

    if (!isOpen) return null;

    const sendMessage = async (messageText?: string) => {
        const textToSend = messageText || input;
        if (!textToSend.trim() && !stagedFile) return;

        // Hide suggestions after first user message
        setShowSuggestions(false);
        setSmartFollowUps([]);

        const userMsg = {
            role: 'user',
            text: textToSend,
            image: stagedPreview
        };
        setMessages([...messages, userMsg]);
        const currentInput = textToSend;
        const currentFile = stagedFile;
        setInput('');
        removeStagedImage();
        setIsLoading(true);
        setTypingAgent('');

        const formData = new FormData();
        formData.append('message', currentInput);
        if (currentFile) {
            formData.append('file', currentFile);
        }
        formData.append('history', JSON.stringify(messages.map(m => ({ role: m.role, content: m.text }))));

        try {
            const res = await authFetch(API.stylist.chat, { method: 'POST', body: formData });
            if (res.ok && res.body) {
                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                setMessages(prev => [...prev, { role: 'assistant', text: '', status: 'Starting...' }]);
                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n\n');
                    buffer = lines.pop() || '';
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const event = JSON.parse(line.slice(6));
                            if (event.type === 'status') {
                                // Extract agent name from status for typing indicator
                                const statusText = event.content;
                                if (statusText.includes('Advisor')) setTypingAgent('Advisor');
                                else if (statusText.includes('Manager')) setTypingAgent('Manager');
                                else if (statusText.includes('Closet')) setTypingAgent('Closet');
                                else if (statusText.includes('Budget')) setTypingAgent('Budget');
                                else if (statusText.includes('Visualizer')) setTypingAgent('Visualizer');
                                else setTypingAgent('Stylist');

                                setMessages(prev => {
                                    const next = [...prev];
                                    next[next.length - 1].status = event.content;
                                    return next;
                                });
                            } else if (event.type === 'chunk') {
                                setMessages(prev => {
                                    const next = [...prev];
                                    const last = next[next.length - 1];
                                    last.text = (last.text || '') + event.content;
                                    return next;
                                });
                            } else if (event.type === 'final') {
                                const botResponse = event.content;
                                setMessages(prev => {
                                    const next = [...prev];
                                    next[next.length - 1] = {
                                        role: 'assistant',
                                        text: botResponse.response,
                                        images: botResponse.images,
                                        suggested_outfits: botResponse.suggested_outfits,
                                        status: undefined
                                    };
                                    return next;
                                });

                                // Generate smart follow-ups based on response
                                const followUps = getSmartFollowUps(botResponse.response, messages);
                                setSmartFollowUps(followUps);
                                setTypingAgent('');

                                if (botResponse.wallet_confirmation?.required) {
                                    const wc = botResponse.wallet_confirmation;
                                    setWalletModalData({
                                        isOpen: true, itemName: wc.item_name, price: wc.price,
                                        currency: wc.currency, balance: wc.current_balance
                                    });
                                }
                            }
                        }
                    }
                }
            }
        } catch (err) { console.error("Chat error:", err); }
        finally { setIsLoading(false); }
    };

    return (
        <div className={styles.drawerOverlay} onClick={onClose}>
            <div className={styles.drawer} onClick={e => e.stopPropagation()}>
                <div className={styles.drawerHeader}>
                    <div className={styles.headerTitle}>
                        <div className={styles.statusDot}></div>
                        <h3>Add Outfit</h3>
                        {user?.wallet_balance !== undefined && (
                            <span className={styles.budgetBadge}>
                                Balance: {user.wallet_balance} {user.currency || 'TND'}
                            </span>
                        )}
                    </div>
                    <button className={styles.closeBtn} onClick={onClose}>✕</button>
                </div>

                <div className={styles.chatBody}>
                    {/* Suggested Prompts - Show on first open */}
                    {showSuggestions && messages.length === 1 && (
                        <div className={styles.suggestionsContainer}>
                            <p className={styles.suggestionsTitle}>💡 Quick Actions</p>
                            <div className={styles.promptGrid}>
                                {SUGGESTED_PROMPTS.map((prompt, idx) => (
                                    <button
                                        key={idx}
                                        className={styles.promptChip}
                                        onClick={() => sendMessage(prompt.text)}
                                    >
                                        <span className={styles.promptIcon}>{prompt.icon}</span>
                                        <span className={styles.promptText}>{prompt.text}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {messages.map((msg, i) => (
                        <div key={i} className={`${styles.message} ${styles[msg.role]}`}>
                            <div className={styles.bubble}>
                                {msg.image && (
                                    <img src={msg.image} alt="User upload" className={styles.userUploadPreview} />
                                )}
                                <div className={styles.textContent}>{renderMarkdown(msg.text)}</div>
                                {msg.status && (
                                    <div className={`${styles.streamingStatus} ${msg.status.toLowerCase().includes('sketching') ? styles.visualizingStatus : ''}`}>
                                        <span className={styles.statusPulse}></span>
                                        {msg.status}
                                    </div>
                                )}
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
                                            <button
                                                key={idx}
                                                className={styles.fitBadge}
                                                onClick={() => userPhoto && setTryOnData({ items: fit.item_details || [] })}
                                            >
                                                ✨ {fit.name} ({fit.score}/10)
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {/* Enhanced Typing Indicator */}
                    {isLoading && (!messages.length || !messages[messages.length - 1].status) && (
                        <div className={`${styles.message} ${styles.assistant}`}>
                            <div className={styles.typingBubble}>
                                <div className={styles.typingDots}>
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                </div>
                                {typingAgent && (
                                    <p className={styles.typingText}>{typingAgent} is thinking...</p>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Smart Follow-ups */}
                    {!isLoading && smartFollowUps.length > 0 && (
                        <div className={styles.followUpsContainer}>
                            <p className={styles.followUpsTitle}>What's next?</p>
                            <div className={styles.followUpsGrid}>
                                {smartFollowUps.map((followUp, idx) => (
                                    <button
                                        key={idx}
                                        className={styles.followUpChip}
                                        onClick={() => sendMessage(followUp.text)}
                                    >
                                        <span>{followUp.icon}</span>
                                        <span>{followUp.text}</span>
                                    </button>
                                ))}
                            </div>
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
                        text: `Great! I've updated your wallet. Your new balance is **${newBalance} ${walletModalData.currency}**.`
                    }]);
                }}
            />
        </div>
    );
};

export default AIStylistAssistant;
