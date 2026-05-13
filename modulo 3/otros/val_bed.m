%prueba BED 
clc 
D=40;
%BED=64 segun Cremonessi 

alfa_beta=2.5; %Gy
lamda=log(2)/64.1; %h 
mu=log(2)/2.5; %h

G=lamda/(mu+lamda);
BED=D.^2.*G;
BED=BED/alfa_beta;
BED=BED+D;

%OK