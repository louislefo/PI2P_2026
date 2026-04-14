export const formatTime = (date) => {
  return date.toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  });
};

export const formatDate = (isoString) => {
  const date = new Date(isoString);
  return date.toLocaleString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  });
};

export const formatFullDate = (isoString) => {
  const date = new Date(isoString);
  return date.toLocaleDateString('fr-FR', {
    day: '2-digit', month: 'short', year: 'numeric'
  });
};

export const isAuthorized = (statusText) => {
  if (!statusText) return true;
  const lower = statusText.toLowerCase();
  return !lower.includes('denied') && !lower.includes('refusé') && !lower.includes('blacklist');
};
