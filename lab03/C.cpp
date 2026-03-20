#include <iostream>
#include <cstring>
#include <string>
#include <netdb.h>
#include <arpa/inet.h>
#include <unistd.h>

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "Usage: " << argv[0] << " <server_host> <server_port> <filename>" << std::endl;
        return 1;
    }

    std::string host = argv[1];
    int port = std::stoi(argv[2]);
    std::string filename = argv[3];

    hostent* server = gethostbyname(host.c_str());
    if (!server) {
        std::cerr << "no such host" << std::endl;
        return 1;
    }

    int sock = socket(AF_INET, SOCK_STREAM, 0);

    sockaddr_in server_addr{};
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    std::memcpy(&server_addr.sin_addr.s_addr, server->h_addr, server->h_length);

    if (connect(sock, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        std::cerr << "connection failed" << std::endl;
        return 1;
    }

    std::string request =
        "GET /" + filename + " HTTP/1.1\r\n"
        "Host: " + host + "\r\n"
        "Connection: close\r\n"
        "\r\n";

    send(sock, request.c_str(), request.size(), 0);

    char buffer[4096];
    int bytes;

    while ((bytes = read(sock, buffer, sizeof(buffer))) > 0) {
        std::cout.write(buffer, bytes);
    }

    close(sock);
    return 0;
}