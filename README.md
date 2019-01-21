# Auto scaling mechanism of AWS Cloud with Predictive Scaling

## Introduction
The auto-scaling mechanism is a means used to cope with changes in traffic load. Although it is mainly used to cope with predictable changes that arise from known characteristics of the service (i.e., peak hours), it is also used to cope with unpredictable loads that may arise from flash crowds or malicious Distributed Denial of Service (DDoS) attacks. Using auto-scaling, machines can be added and removed in an on-line manner to respond to fluctuating load. 

The Yo-Yo attack, is a new attack against the auto-scaling mechanism in which the attacker sends periodic bursts of overload. The Yo-Yo attack is harder to detect and requires less resources from the attacker compared to traditional DDoS.The analysis of the Yo-Yo attack given in ‘DDoS Attack on Cloud Auto-scaling Mechanisms’, by Anat Bremler-Barr et al, demonstrates how this attack can cause significant performance degradation and economic damage when the auto-scaling mechanism is used.

Predictive Scaling is a new Auto Scaling mechanism introduced by AWS in November 2018.
AWS collects data from actual EC2 usage and further informed by billions of data points drawn from their observations, and uses well-trained Machine Learning models to predict the expected traffic (and EC2 usage) including daily and weekly patterns.
With its predictions, Predictive Scaling should handle DDoS attacks, and also reduce computing costs.

I our project we will attempt to analyze the added effect of the new auto scaling mechanism on the outcome of a Yo-Yo attack. Our goal is to define an environment that will be comparable to the one described in the paper with the addition of the auto scaling mechanism.

## Related Work: 
<i>Discuss prior work and the landscape of the area </i>

## Technical details
In order to compare our results with those of the paper, we use the same environment as described in it. The only difference is the auto scaling group which will be changed to a predictive one instead of adaptive / descriptive.

The model is very simplified and basic that uses the parameters of a medium-size e-commerce web site. We assume the site has, in steady state, an average rate of 10,000 dynamic requests per minute, with 10 machines. As in the paper, we define power of the attack as the extra load per machine during the attack, which in our case is equal to 2. Thus the site is attacked with an additional 20,000 requests per minute (triple the average request rate).

Consider a common setting in Cloud environment that includes identical service machines behind a load balancer. Requests arrive with an average rate of r requests per unit time, and the load balancer distributes them to m machines in the steady state.
Our environment in AWS consists of a simple HTTP server.
In our experiments, we begin with a single machine. In the steady state our http server handles 10 dynamic http requests per second, and in the on-attack phase, our attacker implements an attack with power of attack 4, i.e., adds an additional 40 requests per second.

There are 4 scaling strategies in AWS auto scaling groups: Optimize for availability, Balance availability and cost, Optimize for cost and Custom.
In our experiment we choose to focus on optimize for cost in order to cause Economic Dentail of Sustainability (EDoS) attack to our server. We’ll use Amazon CloudWatch to monitor our instances.

Because the predictive scaling mechanism is re-evaluated every 24 hours and creates a forecast for the next 48 hours, we intend to examine the affect of 2 subsequent days in which we will perform a yo-yo attack. We expect that on the second day, the predictive scaling method will be adjust an a way that anticipates the attack. On the third day we would like to observe the behaviour of the predictive scaling mechanism in absence   

We will analyze the added affect of the new auto scaling mechanism on the outcome of a Yo-Yo attack using figures we will produce. Those figures will contain the response time and error percentage on attack period, and number of machines and CPU utilization on attack period.

## Evaluation  and discussion:  
<i>Present the experimental setup in details. Describe the results in figures or tables and text, discuss the meaning of the results and what the reader should take away. describe the limitations and weaknesses of your system. You may propose a plan for future work in the area. </i>

## Conclusion: Conclude your project

## Bibliography:  
- https://github.com/radotzki/aws-predictive-scaling
- http://www.deepness-lab.org/pubs/infocom17_ddos.pdf


