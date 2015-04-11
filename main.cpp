#include <iostream>    //cout
#include <stdio.h> //printf
#include <string.h>    //strlen
#include <string>  //string
#include <sys/socket.h>    //socket
#include <arpa/inet.h> //inet_addr
#include <netdb.h> //hostent

using namespace std;

class tcp_client
{
private:
    int sock;
    std::string address;
    int port;
    struct sockaddr_in server;
     
public:
    tcp_client();
    bool conn(string, int);
    bool send_data(string data);
    string receive(int);
};
 
tcp_client::tcp_client()
{
	// configure this value later
    sock = -1;
    port = 0;
    address = "";
}

int main ()
{
	int sockfd, newsockfd, portno, clilen, n;
    cout << "Hello World" << endl;
    return 0;
}