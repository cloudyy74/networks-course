#include <sstream>
#include <string>
#include <fstream>
#include <iostream>
#include <unistd.h>
#include <netinet/in.h>
#include <optional>

std::optional<std::string> read_file(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file) {
        return std::nullopt;
    }

    std::ostringstream oss;
    oss << file.rdbuf();
    return oss.str();
}

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <server_port>" << std::endl;
        return 1;
    }

    int port = std::stoi(argv[1]);
    int server_fd = socket(AF_INET, SOCK_STREAM, 0);

    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(port);

    if (bind(server_fd, (struct sockaddr*)&address, sizeof(address)) < 0) {
        std::cerr << "bind failed" << std::endl;
        return 1;
    }
    listen(server_fd, 5);

    std::cout << "Server running on port " << port << "...\n";

    while (true) {
        socklen_t addrlen = sizeof(address);
        int client = accept(server_fd, (struct sockaddr*)&address, &addrlen);

        char buffer[4096] = {0};
        read(client, buffer, sizeof(buffer));

        std::istringstream request(buffer);
        std::string method, path, version;
        request >> method >> path >> version;

        std::string file_path = "." + path;

        std::optional<std::string> body = read_file(file_path);
        std::string response;

        if (!body) {
            std::string not_found = "404 Not Found";
            response =
                "HTTP/1.1 404 Not Found\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: " + std::to_string(not_found.size()) + "\r\n"
                "\r\n" +
                not_found;
        } else {
            response =
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: " + std::to_string((*body).size()) + "\r\n"
                "\r\n" +
                *body;
        }
        send(client, response.c_str(), response.size(), 0);
        close(client);
    }

    return 0;
}