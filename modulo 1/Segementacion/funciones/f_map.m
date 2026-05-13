function [map]=f_map(varargin)


%%para mandar las caribles cuando no es necesario que mande todas
if nargin>=1,nmap=varargin{1,1};end  
if nargin==2,color=varargin{1,2};end

map=gray(nmap);
map(nmap+6,:)=[1 0 0]; %%rojo
map(nmap+2,:)=[0 0 1]; %%azul
map(nmap+3,:)=[0 1 0]; %%verde
map(nmap+4,:)=[1 0 1]; %%magenta
map(nmap+5,:)=[0 1 1]; %%cian
map(nmap+1,:)=[1 1 0]; %%amarillo yellow

if nargin==2;map(nmap+7,:)=color;end   
return 
