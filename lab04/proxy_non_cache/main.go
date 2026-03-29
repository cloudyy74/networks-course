package main

import (
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"
)

const listenAddr = ":8080"

var (
	logFile *os.File
	logMu   sync.Mutex
)

func buildTargetURL(requestURI string) (string, error) {
	raw := strings.TrimPrefix(requestURI, "/")
	if raw == "" {
		return "", fmt.Errorf("empty request uri")
	}

	res := "http://" + raw
	_, err := url.Parse(res)
	if err != nil {
		return "", err
	}

	return res, nil
}

func copyHeaders(dst, src http.Header) {
	for k, values := range src {
		for _, v := range values {
			dst.Add(k, v)
		}
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

	req, err := http.NewRequest(r.Method, targetURL, r.Body)
	if err != nil {
		http.Error(w, "Bad Request", http.StatusBadRequest)
		return
	}

	copyHeaders(req.Header, r.Header)

	client := &http.Client{Timeout: 5 * time.Second}

	resp, err := client.Do(req)
	if err != nil {
		http.Error(w, "Bad Gateway", http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	writeLog(targetURL, resp.StatusCode)

	copyHeaders(w.Header(), resp.Header)

	w.WriteHeader(resp.StatusCode)
	if resp.Body != nil {
		io.Copy(w, resp.Body)
	}
}

func writeLog(url string, code int) {
	logMu.Lock()
	defer logMu.Unlock()
	fmt.Fprintf(logFile, "%s %d\n", url, code)
}

func main() {
	logFile, _ = os.OpenFile("proxy.log", os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	defer logFile.Close()

	http.HandleFunc("/", proxyHandler)
	http.ListenAndServe(":8080", nil)
}
