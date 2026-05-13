function [EUD] = f_EUD(Phantom,D,organo,alfa)


ind=Phantom==organo;

D1=D(ind);
n=length(D1);

EUD=-alfa.*D1;
EUD=exp(EUD);
EUD=sum(EUD)/n;
EUD=log(EUD);
EUD=-EUD/alfa;

end

