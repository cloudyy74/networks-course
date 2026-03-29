package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

const (
	listenAddr = ":8080"
	cacheDir   = "cache"
)

var (
	logFile *os.File
	logMu   sync.Mutex
)

type cacheEntry struct {
	URL          string      `json:"url"`
	StatusCode   int         `json:"status_code"`
	Header       http.Header `json:"header"`
	LastModified string      `json:"last_modified,omitempty"`
	ETag         string      `json:"etag,omitempty"`
}

func buildTargetURL(requestURI string) (string, error) {
	raw := strings.TrimPrefix(requestURI, "/")
	if raw == "" {
		return "", fmt.Errorf("empty request uri")
	}

	res := "http://" + raw
	parsed, err := url.Parse(res)
	if err != nil {
		return "", err
	}

	return parsed.String(), nil
}

func copyHeaders(dst, src http.Header) {
	for k, values := range src {
		for _, v := range values {
			dst.Add(k, v)
		}
	}
}

func cloneHeaders(src http.Header) http.Header {
	dst := make(http.Header, len(src))
	copyHeaders(dst, src)
	return dst
}

func cacheKey(targetURL string) string {
	sum := sha256.Sum256([]byte(targetURL))
	return hex.EncodeToString(sum[:])
}

func cacheMetaPath(targetURL string) string {
	return filepath.Join(cacheDir, cacheKey(targetURL)+".json")
}

func cacheBodyPath(targetURL string) string {
	return filepath.Join(cacheDir, cacheKey(targetURL)+".body")
}

func readCacheEntry(targetURL string) (cacheEntry, []byte, error) {
	metaPath := cacheMetaPath(targetURL)
	bodyPath := cacheBodyPath(targetURL)

	metaBytes, err := os.ReadFile(metaPath)
	if err != nil {
		return cacheEntry{}, nil, err
	}

	var entry cacheEntry
	if err := json.Unmarshal(metaBytes, &entry); err != nil {
		return cacheEntry{}, nil, err
	}

	body, err := os.ReadFile(bodyPath)
	if err != nil {
		return cacheEntry{}, nil, err
	}

	return entry, body, nil
}

func writeCacheEntry(targetURL string, resp *http.Response, body []byte) error {
	entry := cacheEntry{
		URL:          targetURL,
		StatusCode:   resp.StatusCode,
		Header:       cloneHeaders(resp.Header),
		LastModified: resp.Header.Get("Last-Modified"),
		ETag:         resp.Header.Get("ETag"),
	}

	metaBytes, err := json.MarshalIndent(entry, "", "  ")
	if err != nil {
		return err
	}

	if err := os.WriteFile(cacheBodyPath(targetURL), body, 0644); err != nil {
		return err
	}

	if err := os.WriteFile(cacheMetaPath(targetURL), metaBytes, 0644); err != nil {
		return err
	}

	return nil
}

func writeCachedResponse(w http.ResponseWriter, entry cacheEntry, body []byte) {
	copyHeaders(w.Header(), entry.Header)
	w.WriteHeader(entry.StatusCode)
	if len(body) > 0 {
		w.Write(body)
	}
}

func proxyHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodPost {
		http.Error(w, "Only GET and POST are supported", http.StatusMethodNotAllowed)
		return
	}

	targetURL, err := buildTargetURL(r.RequestURI)
	if err != nil {
		http.Error(w, "Bad URL", http.StatusBadRequest)
		return
	}

	var (
		cachedEntry cacheEntry
		cachedBody  []byte
		hasCache    bool
	)

	if r.Method == http.MethodGet {
		entry, body, err := readCacheEntry(targetURL)
		if err == nil {
			cachedEntry = entry
			cachedBody = body
			hasCache = true
		}
	}

	req, err := http.NewRequest(r.Method, targetURL, r.Body)
	if err != nil {
		http.Error(w, "Bad Request", http.StatusBadRequest)
		return
	}

	req.Header = cloneHeaders(r.Header)
	if hasCache {
		if cachedEntry.LastModified != "" {
			req.Header.Set("If-Modified-Since", cachedEntry.LastModified)
		}
		if cachedEntry.ETag != "" {
			req.Header.Set("If-None-Match", cachedEntry.ETag)
		}
	}

	client := &http.Client{Timeout: 5 * time.Second}

	resp, err := client.Do(req)
	if err != nil {
		http.Error(w, "Bad Gateway", http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotModified && hasCache {
		writeCachedResponse(w, cachedEntry, cachedBody)
		writeLog(targetURL, cachedEntry.StatusCode, "(cached)")
		return
	}

	writeLog(targetURL, resp.StatusCode, "")

	copyHeaders(w.Header(), resp.Header)
	w.WriteHeader(resp.StatusCode)

	if resp.Body == nil {
		return
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		http.Error(w, "Bad Gateway", http.StatusBadGateway)
		return
	}

	if _, err := w.Write(body); err != nil {
		return
	}

	if r.Method == http.MethodGet && resp.StatusCode == http.StatusOK {
		writeCacheEntry(targetURL, resp, body)
	}
}

func writeLog(url string, code int, cacheStatus string) {
	logMu.Lock()
	defer logMu.Unlock()
	fmt.Fprintf(logFile, "%s %d %s\n", url, code, cacheStatus)
}

func main() {
	if err := os.MkdirAll(cacheDir, 0755); err != nil {
		panic(err)
	}

	var err error
	logFile, err = os.OpenFile("proxy.log", os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		panic(err)
	}
	defer logFile.Close()

	http.HandleFunc("/", proxyHandler)
	http.ListenAndServe(listenAddr, nil)
}
