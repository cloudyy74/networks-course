package main

import (
	"encoding/json"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"sync"
)

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

type Product struct {
	ID          int    `json:"id"`
	Name        string `json:"name"`
	Description string `json:"description"`
	Icon        string `json:"icon"`
	Deleted     bool   `json:"-"`
}

type createProductRequest struct {
	Name        string `json:"name"`
	Description string `json:"description"`
}

type updateProductRequest struct {
	Name        *string `json:"name"`
	Description *string `json:"description"`
}

var (
	products  []Product
	mu        sync.Mutex
	imagesDir string = "./product_images"
)

func createProduct(w http.ResponseWriter, r *http.Request) {
	body, _ := io.ReadAll(r.Body)
	var req createProductRequest
	if err := json.Unmarshal(body, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return
	}

	mu.Lock()
	defer mu.Unlock()
	id := len(products)

	p := Product{
		ID:          id,
		Name:        req.Name,
		Description: req.Description,
		Icon:        "",
		Deleted:     false,
	}

	products = append(products, p)

	writeJSON(w, http.StatusCreated, p)
}

func getExistingProduct(id int) (*Product, bool) {
	if id < 0 || id >= len(products) {
		return nil, false
	}
	if products[id].Deleted {
		return nil, false
	}
	return &products[id], true
}

func getProduct(w http.ResponseWriter, r *http.Request) {
	idStr := r.PathValue("product_id")

	id, err := strconv.Atoi(idStr)
	if err != nil || id < 0 {
		writeError(w, http.StatusBadRequest, "invalid product_id")
		return
	}

	mu.Lock()
	defer mu.Unlock()
	p, ok := getExistingProduct(id)

	if !ok {
		writeError(w, http.StatusNotFound, "product not found")
		return
	}

	writeJSON(w, http.StatusOK, p)
}

func updateProduct(w http.ResponseWriter, r *http.Request) {
	idStr := r.PathValue("product_id")

	id, err := strconv.Atoi(idStr)
	if err != nil || id < 0 {
		writeError(w, http.StatusBadRequest, "invalid product_id")
		return
	}

	mu.Lock()
	defer mu.Unlock()
	p, ok := getExistingProduct(id)

	if !ok {
		writeError(w, http.StatusNotFound, "product not found")
		return
	}

	body, _ := io.ReadAll(r.Body)

	var req updateProductRequest
	if err := json.Unmarshal(body, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return
	}

	if req.Name != nil {
		p.Name = *req.Name
	}
	if req.Description != nil {
		p.Description = *req.Description
	}

	writeJSON(w, http.StatusOK, p)
}

func deleteProduct(w http.ResponseWriter, r *http.Request) {
	idStr := r.PathValue("product_id")

	id, err := strconv.Atoi(idStr)
	if err != nil || id < 0 {
		writeError(w, http.StatusBadRequest, "invalid product_id")
		return
	}

	mu.Lock()
	defer mu.Unlock()
	p, ok := getExistingProduct(id)
	if !ok {
		writeError(w, http.StatusNotFound, "product not found")
		return
	}

	p.Deleted = true

	writeJSON(w, http.StatusOK, p)
}

func listProducts(w http.ResponseWriter, r *http.Request) {
	mu.Lock()
	defer mu.Unlock()
	out := make([]Product, 0, len(products))
	for _, p := range products {
		if !p.Deleted {
			out = append(out, p)
		}
	}

	writeJSON(w, http.StatusOK, out)
}

func uploadProductImage(w http.ResponseWriter, r *http.Request) {
	idStr := r.PathValue("product_id")
	id, err := strconv.Atoi(idStr)
	if err != nil || id < 0 {
		writeError(w, http.StatusBadRequest, "invalid product_id")
		return
	}

	mu.Lock()
	defer mu.Unlock()
	p, ok := getExistingProduct(id)
	if !ok {
		writeError(w, http.StatusNotFound, "product not found")
		return
	}

	if err := r.ParseMultipartForm(10 << 20); err != nil { // 10MB
		writeError(w, http.StatusBadRequest, "expected multipart/form-data less than 10 MB")
		return
	}

	file, header, err := r.FormFile("icon")
	if err != nil {
		writeError(w, http.StatusBadRequest, `file field "icon" is required`)
		return
	}
	defer file.Close()

	if err := os.MkdirAll(imagesDir, 0o755); err != nil {
		writeError(w, http.StatusInternalServerError, "cannot create images dir")
		return
	}

	filename := strconv.Itoa(id) + "_" + filepath.Base(header.Filename)
	savePath := filepath.Join(imagesDir, filename)

	dst, err := os.Create(savePath)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "cannot save file")
		return
	}
	defer dst.Close()

	if _, err := io.Copy(dst, file); err != nil {
		writeError(w, http.StatusInternalServerError, "cannot write file")
		return
	}

	p.Icon = savePath
	writeJSON(w, http.StatusOK, p)
}

func getProductImage(w http.ResponseWriter, r *http.Request) {
	idStr := r.PathValue("product_id")
	id, err := strconv.Atoi(idStr)
	if err != nil || id < 0 {
		writeError(w, http.StatusBadRequest, "invalid product_id")
		return
	}

	mu.Lock()
	defer mu.Unlock()
	p, ok := getExistingProduct(id)
	if !ok {
		writeError(w, http.StatusNotFound, "product not found")
		return
	}

	iconPath := p.Icon
	if iconPath == "" {
		writeError(w, http.StatusNotFound, "image not uploaded")
		return
	}

	http.ServeFile(w, r, iconPath)
}

func main() {
	http.HandleFunc("POST /product", createProduct)
	http.HandleFunc("GET /product/{product_id}", getProduct)
	http.HandleFunc("PUT /product/{product_id}", updateProduct)
	http.HandleFunc("DELETE /product/{product_id}", deleteProduct)
	http.HandleFunc("GET /products", listProducts)
	http.HandleFunc("POST /product/{product_id}/image", uploadProductImage)
	http.HandleFunc("GET /product/{product_id}/image", getProductImage)
	http.ListenAndServe(":8080", nil)
}
