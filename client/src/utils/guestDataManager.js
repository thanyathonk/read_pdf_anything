/**
 * Guest Data Manager
 * Manages localStorage data for guest users with auto-expiry
 */

const EXPIRY_DURATION_MS = 24 * 60 * 60 * 1000; // 1 day in milliseconds

/**
 * Save guest data with timestamp
 */
export const saveGuestData = (key, data) => {
  const dataWithTimestamp = {
    data,
    timestamp: Date.now(),
  };
  localStorage.setItem(key, JSON.stringify(dataWithTimestamp));
};

/**
 * Load guest data and check if expired
 * Returns null if expired or not found
 */
export const loadGuestData = (key) => {
  try {
    const saved = localStorage.getItem(key);
    if (!saved) return null;

    const parsed = JSON.parse(saved);
    
    // Check if old format (no timestamp)
    if (!parsed.timestamp) {
      // Migrate old data by adding timestamp
      const dataWithTimestamp = {
        data: parsed,
        timestamp: Date.now(),
      };
      localStorage.setItem(key, JSON.stringify(dataWithTimestamp));
      return parsed; // Return old data for this session
    }

    // Check expiry
    const age = Date.now() - parsed.timestamp;
    if (age > EXPIRY_DURATION_MS) {
      // Data expired, remove it
      localStorage.removeItem(key);
      console.log(`[Guest Data] Expired and removed: ${key}`);
      return null;
    }

    return parsed.data;
  } catch (error) {
    console.error(`[Guest Data] Failed to load ${key}:`, error);
    return null;
  }
};

/**
 * Check if guest data is expired
 */
export const isGuestDataExpired = (key) => {
  try {
    const saved = localStorage.getItem(key);
    if (!saved) return true;

    const parsed = JSON.parse(saved);
    if (!parsed.timestamp) return false; // Old data, not expired yet

    const age = Date.now() - parsed.timestamp;
    return age > EXPIRY_DURATION_MS;
  } catch (error) {
    return true;
  }
};

/**
 * Clear all expired guest data
 */
export const clearExpiredGuestData = () => {
  const guestKeys = [
    'guest_pdf_files',
    'guest_chat_messages',
  ];

  guestKeys.forEach((key) => {
    // localStorage.removeItem(key)
    if (isGuestDataExpired(key)) {
      localStorage.removeItem(key);
      console.log(`[Guest Data] Cleared expired: ${key}`);
    }
  });
};

/**
 * Clear all guest data (on logout or manual clear)
 */
export const clearAllGuestData = () => {
  const guestKeys = [
    'guest_pdf_files',
    'guest_chat_messages',
  ];

  guestKeys.forEach((key) => {
    localStorage.removeItem(key);
  });
  
  console.log('[Guest Data] All guest data cleared');
};

/**
 * Get remaining time until expiry in hours
 */
export const getTimeUntilExpiry = (key) => {
  try {
    const saved = localStorage.getItem(key);
    if (!saved) return 0;

    const parsed = JSON.parse(saved);
    if (!parsed.timestamp) return 24; // Old data, assume full 24 hours

    const age = Date.now() - parsed.timestamp;
    const remainingMs = EXPIRY_DURATION_MS - age;
    const remainingHours = Math.max(0, remainingMs / (60 * 60 * 1000));
    
    return remainingHours;
  } catch (error) {
    return 0;
  }
};
