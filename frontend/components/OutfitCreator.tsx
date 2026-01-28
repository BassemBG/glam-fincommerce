"use client";
import React, { useState, useEffect } from 'react';
import styles from './FloatingStylist.module.css'; // Reusing styles for now
import TryOnVisualizer from './TryOnVisualizer';
import { API } from '../lib/api';
import { authFetch } from '../lib/auth';
import { useAuthGuard } from '../lib/useAuthGuard';

interface OutfitCreatorProps {
    isOpen: boolean;
    onClose: () => void;
}

const OutfitCreator = ({ isOpen, onClose }: OutfitCreatorProps) => {
    const token = useAuthGuard();
    const [messages, setMessages] = useState<any[]>([
        { role: 'assistant', text: "Welcome to the Outfit Creator! Let's build something stunning. Would you like to:\n1. **Generate** a new look for an occasion?\n2. **Search** your closet for specific pieces?\n3. **Visualize** a combination?" }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [tryOnData, setTryOnData] = useState<any>(null);
    const [userPhoto, setUserPhoto] = useState<string | null>(null);
    const [user, setUser] = useState<any>(null);
    const [status, setStatus] = useState<string | null>(null);

    // Manual Selection States
    const [selectionMode, setSelectionMode] = useState(false);
    const [closetItems, setClosetItems] = useState<any[]>([]);
    const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());

    const toggleSelectionMode = async () => {
        if (!selectionMode) {
            setIsLoading(true);
            try {
                const res = await authFetch(API.closet.items);
                if (res.ok) {
                    setClosetItems(await res.json());
                }
            } catch (err) { console.error("Closet fetch error:", err); }
            finally { setIsLoading(false); }
        }
        setSelectionMode(!selectionMode);
    };

    const toggleItemSelection = (itemId: string) => {
        const next = new Set(selectedItems);
        if (next.has(itemId)) next.delete(itemId);
        else next.add(itemId);
        setSelectedItems(next);
    };

    const handleManualTryOn = async () => {
        const selected = closetItems.filter(item => selectedItems.has(item.id));
        if (selected.length === 0) {
            console.warn('[OutfitCreator] No items selected for try-on');
            return;
        }

        console.log('[OutfitCreator] Starting manual try-on with', selected.length, 'items');
        setIsLoading(true);

        try {
            const itemsForBackend = selected.map(item => ({
                id: item.id,
                image_url: item.image_url,
                body_region: item.body_region || item.clothing?.body_region || 'top'
            }));

            console.log('[OutfitCreator] Sending items to backend:', itemsForBackend);
            console.log('[OutfitCreator] API endpoint:', API.stylist.tryon);

            const res = await authFetch(API.stylist.tryon, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ items: itemsForBackend })
            });

            console.log('[OutfitCreator] Response status:', res.status);

            if (res.ok) {
                const data = await res.json();
                console.log('[OutfitCreator] Success! Received data:', data);
                setTryOnData({
                    items: itemsForBackend,
                    itemIds: selected.map(i => i.id),
                    tryonImageUrl: data.url
                });
            } else {
                const errorText = await res.text();
                console.error('[OutfitCreator] Backend error:', res.status, errorText);
                alert(`Try-on failed: ${res.status} - ${errorText.substring(0, 100)}`);
                setTryOnData({
                    items: itemsForBackend,
                    itemIds: selected.map(i => i.id)
                });
            }
        } catch (err) {
            console.error('[OutfitCreator] Try-on error:', err);
            alert(`Error during try-on: ${err instanceof Error ? err.message : 'Unknown error'}`);
            setTryOnData({
                items: selected.map(item => ({
                    id: item.id,
                    image_url: item.image_url,
                    body_region: item.body_region || item.clothing?.body_region || 'top'
                })),
                itemIds: selected.map(i => i.id)
            });
        } finally {
            setIsLoading(false);
            setSelectionMode(false);
            setSelectedItems(new Set());
        }
    };

    const handleSaveOutfit = async () => {
        if (!tryOnData || !tryOnData.itemIds) return;

        setIsLoading(true);
        console.log('[OutfitCreator] Saving outfit with data:', {
            items: tryOnData.itemIds,
            name: tryOnData.name || "My Custom Look",
            occasion: tryOnData.occasion || "Manual Curation",
            vibe: tryOnData.vibe || "Personal",
            score: tryOnData.score || 0,
            tryon_image_url: tryOnData.tryonImageUrl
        });

        try {
            const res = await authFetch(API.outfits.save, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    items: tryOnData.itemIds,
                    name: tryOnData.name || "My Custom Look",
                    occasion: tryOnData.occasion || "Manual Curation",
                    vibe: tryOnData.vibe || "Personal",
                    score: tryOnData.score || 0,
                    reasoning: tryOnData.reasoning || "Created via Outfit Creator",
                    tryon_image_url: tryOnData.tryonImageUrl
                })
            });

            if (res.ok) {
                setMessages(prev => [...prev, { role: 'assistant', text: "✨ Outfit saved to your gallery!" }]);
                setTryOnData(null);
            } else {
                alert("Failed to save outfit");
            }
        } catch (err) {
            console.error("Save error:", err);
            alert("Error saving outfit");
        } finally {
            setIsLoading(false);
        }
    };

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

    if (!isOpen) return null;

    const handleVisualSearch = async (overrideQuery?: string) => {
        const query = overrideQuery || input;
        if (!query.trim()) return;

        setIsLoading(true);
        setStatus(`Looking for ${query}...`);

        try {
            const res = await authFetch(API.stylist.search(query));
            if (res.ok) {
                const results = await res.json();
                setMessages(prev => [...prev,
                { role: 'user', text: `Search: ${query}` },
                {
                    role: 'assistant',
                    text: results.length > 0
                        ? `I found these items matching "**${query}**":`
                        : `I couldn't find any items matching "**${query}**" visually. Try a different description?`,
                    visualResults: results
                }
                ]);
            }
        } catch (err) {
            console.error("Visual search error:", err);
        } finally {
            setIsLoading(false);
            setStatus(null);
            setInput('');
        }
    };

    const sendMessage = async (overrideMessage?: string) => {
        const textToSend = overrideMessage || input;
        if (!textToSend.trim()) return;

        const userMsg = { role: 'user', text: textToSend };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setIsLoading(true);

        const formData = new FormData();
        formData.append('message', textToSend);
        formData.append('history', JSON.stringify(messages.map(m => ({ role: m.role, content: m.text }))));

        try {
            const res = await authFetch(API.stylist.chat, { method: 'POST', body: formData });
            if (res.ok && res.body) {
                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                setMessages(prev => [...prev, { role: 'assistant', text: '', status: 'Creating...' }]);
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
                            }
                        }
                    }
                }
            }
        } catch (err) { console.error("Creation error:", err); }
        finally { setIsLoading(false); }
    };

    const occasions = ["Work", "Casual", "Party", "Gala", "Gym", "Date Night"];

    return (
        <div className={styles.drawerOverlay} onClick={onClose}>
            <div className={styles.drawer} onClick={e => e.stopPropagation()}>
                <div className={styles.drawerHeader}>
                    <div className={styles.headerTitle}>
                        <div className={styles.statusDot}></div>
                        <h3>Outfit Creator</h3>
                    </div>
                    <button className={styles.closeBtn} onClick={onClose}>✕</button>
                </div>

                <div className={styles.chatBody}>
                    <div className={styles.creatorShortcuts}>
                        <div className={styles.shortcutHeader}>
                            <p className={styles.shortcutLabel}>Quick Compose:</p>
                            <button
                                className={`${styles.manualToggle} ${selectionMode ? styles.activeToggle : ''}`}
                                onClick={toggleSelectionMode}
                            >
                                {selectionMode ? "Back to Chat" : "Pick Manually"}
                            </button>
                        </div>

                        {!selectionMode ? (
                            <div className={styles.occasionGrid}>
                                {occasions.map(occ => (
                                    <button
                                        key={occ}
                                        className={styles.occBtn}
                                        onClick={() => sendMessage(`Generate a ${occ} outfit for me using my closet.`)}
                                    >
                                        {occ}
                                    </button>
                                ))}
                            </div>
                        ) : (
                            <div className={styles.selectionInterface}>
                                <div className={styles.selectionGrid}>
                                    {closetItems.map(item => (
                                        <div
                                            key={item.id}
                                            className={`${styles.selectionItem} ${selectedItems.has(item.id) ? styles.itemSelected : ''}`}
                                            onClick={() => toggleItemSelection(item.id)}
                                        >
                                            <img src={item.image_url} alt={item.sub_category} />
                                            {selectedItems.has(item.id) && <div className={styles.checkOverlay}>✓</div>}
                                        </div>
                                    ))}
                                </div>
                                <button
                                    className={styles.finishSelectionBtn}
                                    disabled={selectedItems.size === 0 || isLoading}
                                    onClick={handleManualTryOn}
                                >
                                    {isLoading ? "Generating AI Look..." : `Try On Selected (${selectedItems.size})`}
                                </button>
                            </div>
                        )}
                    </div>

                    {!selectionMode && (
                        <>
                            {messages.map((msg, i) => (
                                <div key={i} className={`${styles.message} ${styles[msg.role]}`}>
                                    <div className={styles.bubble}>
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
                                                        onClick={async () => {
                                                            if (!userPhoto || !fit.item_details) return;

                                                            console.log('[OutfitCreator] Outfit badge clicked:', fit.name);
                                                            setIsLoading(true);
                                                            setStatus("Glam is sketching your virtual try-on... ✨ (this usually takes 60-80s)");

                                                            try {
                                                                // Prepare items for backend
                                                                const itemsForBackend = fit.item_details.map((item: any) => ({
                                                                    id: item.id,
                                                                    image_url: item.image_url,
                                                                    body_region: item.body_region || 'top'
                                                                }));

                                                                console.log('[OutfitCreator] Calling /tryon with items:', itemsForBackend);

                                                                // Call try-on API
                                                                const res = await authFetch(API.stylist.tryon, {
                                                                    method: 'POST',
                                                                    headers: { 'Content-Type': 'application/json' },
                                                                    body: JSON.stringify({ items: itemsForBackend })
                                                                });

                                                                if (res.ok) {
                                                                    const data = await res.json();
                                                                    console.log('[OutfitCreator] Try-on success:', data);
                                                                    setTryOnData({
                                                                        items: itemsForBackend,
                                                                        itemIds: fit.item_details.map((i: any) => i.id),
                                                                        tryonImageUrl: data.url,
                                                                        name: fit.name,
                                                                        score: fit.score,
                                                                        reasoning: fit.reasoning,
                                                                        occasion: fit.occasion || "AI Generated",
                                                                        vibe: fit.vibe || "AI Recommended"
                                                                    });
                                                                } else {
                                                                    console.error('[OutfitCreator] Try-on failed:', res.status);
                                                                    // Still show the collage even if AI generation fails
                                                                    setTryOnData({
                                                                        items: itemsForBackend,
                                                                        itemIds: fit.item_details.map((i: any) => i.id)
                                                                    });
                                                                }
                                                            } catch (err) {
                                                                console.error('[OutfitCreator] Try-on error:', err);
                                                                // Fallback: show items without try-on
                                                                const itemsForBackend = fit.item_details.map((item: any) => ({
                                                                    id: item.id,
                                                                    image_url: item.image_url,
                                                                    body_region: item.body_region || 'top'
                                                                }));
                                                                setTryOnData({
                                                                    items: itemsForBackend,
                                                                    itemIds: fit.item_details.map((i: any) => i.id)
                                                                });
                                                            } finally {
                                                                setIsLoading(false);
                                                                setStatus(null);
                                                            }
                                                        }}
                                                    >
                                                        ✨ {fit.name} ({fit.score}/10)
                                                    </button>
                                                ))}
                                            </div>
                                        )}

                                        {msg.visualResults && (
                                            <div className={styles.selectionGrid}>
                                                {msg.visualResults.map((item: any) => (
                                                    <div
                                                        key={item.id}
                                                        className={`${styles.selectionItem} ${selectedItems.has(item.id) ? styles.itemSelected : ''}`}
                                                        onClick={() => {
                                                            toggleItemSelection(item.id);
                                                            if (!selectionMode) setSelectionMode(true);
                                                            if (!closetItems.find(i => i.id === item.id)) {
                                                                setClosetItems(prev => [...prev, item]);
                                                            }
                                                        }}
                                                    >
                                                        <img src={item.image_url} alt={item.clothing?.sub_category} />
                                                        {selectedItems.has(item.id) && <div className={styles.checkOverlay}>✓</div>}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                            {isLoading && (
                                <div className={`${styles.message} ${styles.assistant}`}>
                                    {status ? (
                                        <div className={styles.statusRow}>
                                            <div className={styles.loadingPulse}></div>
                                            <p>{status}</p>
                                        </div>
                                    ) : (
                                        <div className={styles.typing}>•••</div>
                                    )}
                                </div>
                            )}
                        </>
                    )}
                </div>

                {!selectionMode && (
                    <div className={styles.chatFooter}>
                        <div className={styles.inputRow}>
                            <input
                                type="text"
                                placeholder="Search closet or describe an outfit..."
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                            />
                            <button onClick={() => handleVisualSearch()} className={styles.searchIconBtn} title="Visual Search (CLIP)">
                                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
                            </button>
                            <button onClick={() => sendMessage()} className={styles.sendBtn} disabled={isLoading}>
                                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {tryOnData && userPhoto && (
                <TryOnVisualizer
                    bodyImage={userPhoto}
                    items={tryOnData.items}
                    tryonImageUrl={tryOnData.tryonImageUrl}
                    onSave={handleSaveOutfit}
                    onClose={() => setTryOnData(null)}
                />
            )}
        </div>
    );
};

export default OutfitCreator;
